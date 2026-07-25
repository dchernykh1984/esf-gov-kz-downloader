"""Client for the IS ESF SOAP API at esf.gov.kz.

Only the read side is implemented: open a session with a signed ticket, page
through incoming invoices and acts, close the session.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from zeep import Client

from app.documents import act_recipient_tins

BASE_URL = "https://esf.gov.kz:8443/esf-web/ws/api1"

# Every status a document can carry. The API has no "any status" wildcard, and
# for acts the status list is a required field, so "all" is spelled out.
INVOICE_STATUSES = (
    "IN_QUEUE",
    "IN_PROCESSING",
    "CREATED",
    "DELIVERED",
    "CANCELED",
    "CANCELED_BY_OGD",
    "CANCELED_BY_SNT_DECLINE",
    "CANCELED_BY_SNT_REVOKE",
    "REVOKED",
    "IMPORTED",
    "DRAFT",
    "FAILED",
    "DELETED",
    "DECLINED",
    "SEND_TO_ISGO",
    "WAIT_BIOMETRICS_VERIFICATION",
    "FAILED_BIOMETRICS_VERIFICATION",
    "DELETED_BIOMETRICS_VERIFICATION",
    "WAITING_CUSTOMER_CONFIRMATION",
    "WAITING_CUSTOMER_REVOKE_CONFIRMATION",
)

AWP_STATUSES = (
    "DRAFT",
    "NOT_VIEWED",
    "DELIVERED",
    "CREATED",
    "IMPORTED",
    "FAILED",
    "CONFIRMED",
    "DECLINED",
    "REVOKED",
    "IN_TERMINATING",
    "TERMINATED",
    "CANCELED",
)


class ApiError(RuntimeError):
    """Raised when the API rejects a call."""


@dataclass
class Document:
    """One downloaded document: its XML body plus the fields we file it by."""

    kind: str
    registration_number: str
    status: str
    body: str


def _awp_timestamp(moment: datetime) -> str:
    """Format a moment the way the acts service expects it (it takes a string)."""
    return moment.isoformat(timespec="milliseconds")


class EsfApi:
    """Session-scoped access to the document services."""

    def __init__(self, base_url: str = BASE_URL) -> None:
        self._base_url = base_url.rstrip("/")
        self._session_id: str | None = None
        self._clients: dict[str, Client] = {}

    def _service(self, name: str):
        if name not in self._clients:
            self._clients[name] = Client(f"{self._base_url}/{name}?wsdl")
        return self._clients[name].service

    @property
    def session_id(self) -> str:
        if self._session_id is None:
            raise ApiError("the session is not open")
        return self._session_id

    def open_session(self, iin: str, tin: str, sign: Callable[[str], str]) -> None:
        """Authenticate: take a ticket, have `sign` sign it, exchange for a session."""
        ticket = self._service("AuthService").createAuthTicket(iin=iin, ttlInMinutes=30)
        self._session_id = self._service("SessionService").createSessionSigned(
            tin=tin,
            signedAuthTicket=sign(ticket),
            sourceType="OTHER",
        )

    def close_session(self) -> None:
        """Close the session. The API asks that this always be done."""
        if self._session_id is None:
            return
        self._service("SessionService").closeSession(sessionId=self._session_id)
        self._session_id = None

    def profiles(self) -> list:
        """Companies the authenticated key may act for."""
        result = self._service("SessionService").currentUserProfiles(
            sessionId=self.session_id
        )
        return result.profileInfo or []

    def incoming_invoices(
        self, date_from: datetime, date_to: datetime, statuses: list[str]
    ) -> Iterator[Document]:
        """Yield incoming invoices issued within the period."""
        service = self._service("InvoiceService")
        for page in self._pages(
            lambda page_num: service.queryInvoice(
                sessionId=self.session_id,
                criteria={
                    "direction": "INBOUND",
                    "dateFrom": date_from,
                    "dateTo": date_to,
                    "invoiceStatusList": {"invoiceStatus": statuses},
                    "asc": True,
                    "pageNum": page_num,
                },
            )
        ):
            for info in page.invoiceInfoList.invoiceInfo or []:
                yield Document(
                    kind="esf",
                    registration_number=info.registrationNumber,
                    status=info.invoiceStatus,
                    body=info.invoiceBody,
                )

    def acts(
        self, date_from: datetime, date_to: datetime, statuses: list[str], tin: str
    ) -> Iterator[Document]:
        """Yield incoming acts within the period.

        The acts service has no direction filter, so both directions come back
        and the incoming ones are picked out by matching the recipient against
        our own BIN.
        """
        service = self._service("AwpWebService")
        for page in self._pages(
            lambda page_num: service.queryAwp(
                sessionId=self.session_id,
                dateFrom=_awp_timestamp(date_from),
                dateTo=_awp_timestamp(date_to),
                statuses={"status": statuses},
                pageNum=page_num,
            )
        ):
            for info in page.awpInfoList.awpInfo or []:
                if tin not in act_recipient_tins(info.awpBody):
                    continue
                yield Document(
                    kind="awp",
                    registration_number=info.registrationNumber,
                    status=info.status,
                    body=info.awpBody,
                )

    @staticmethod
    def _pages(query: Callable[[int | None], Any]) -> Iterator[Any]:
        """Walk result pages until the API says the last one was served.

        The first call leaves pageNum unset so the API picks its own first
        page, which sidesteps guessing whether numbering starts at 0 or 1.
        """
        page_num: int | None = None
        while True:
            page = query(page_num)
            yield page
            if page.lastBlock:
                return
            page_num = page.currPage + 1
