"""XMLDsig signing through a local NCANode instance.

IS ESF authenticates by handing out an XML ticket that the client signs with
its NCA RK key. Keys issued since 2023 use GOST 2015, which no pure-python
library can handle, so the signing is delegated to NCANode over HTTP.
"""

from __future__ import annotations

import base64
from pathlib import Path

import requests

DEFAULT_URL = "http://localhost:14579"


class SigningError(RuntimeError):
    """Raised when the ticket could not be signed."""


def sign_xml(
    xml: str,
    key_path: Path,
    key_password: str,
    ncanode_url: str = DEFAULT_URL,
    timeout: int = 60,
) -> str:
    """Return `xml` signed as XMLDsig with the key stored in `key_path`."""
    try:
        key = base64.b64encode(key_path.read_bytes()).decode("ascii")
    except OSError as exc:
        raise SigningError(f"cannot read the key at {key_path}: {exc}") from exc

    endpoint = f"{ncanode_url.rstrip('/')}/xml/sign"
    payload = {"xml": xml, "signers": [{"key": key, "password": key_password}]}

    try:
        response = requests.post(endpoint, json=payload, timeout=timeout)
    except requests.RequestException as exc:
        raise SigningError(
            f"NCANode is not reachable at {ncanode_url}. Start it and retry. ({exc})"
        ) from exc

    if response.status_code != requests.codes.ok:
        raise SigningError(
            f"NCANode returned HTTP {response.status_code}: {response.text[:300]}"
        )

    body = response.json()
    signed = body.get("xml")
    if not signed:
        raise SigningError(f"NCANode did not return a signature: {body.get('message')}")
    return signed
