"""Reading the XML bodies of invoices and acts.

Documents arrive namespaced (`v2.esf`, `v1.awp`, ...) and the namespace differs
between document versions. Since the layouts differ only by which optional
fields are present, namespaces are stripped on parse and everything is
addressed by plain tag name.
"""

from __future__ import annotations

from collections.abc import Iterator
from xml.etree import ElementTree

from defusedxml.ElementTree import fromstring


class Node:
    """A thin wrapper over an XML element that reads well inside a template.

    A missing field yields an empty node, which renders as "" and is falsy, so
    templates can name optional fields without guarding every one of them.
    """

    __slots__ = ("_element",)

    def __init__(self, element: ElementTree.Element | None = None) -> None:
        self._element = element

    def __getattr__(self, name: str) -> Node:
        if self._element is None:
            return Node()
        return Node(self._element.find(name))

    def all(self, name: str) -> list[Node]:
        """Every child with this tag."""
        if self._element is None:
            return []
        return [Node(child) for child in self._element.findall(name)]

    def __iter__(self) -> Iterator[Node]:
        if self._element is None:
            return iter(())
        return (Node(child) for child in self._element)

    def __str__(self) -> str:
        if self._element is None or self._element.text is None:
            return ""
        return self._element.text.strip()

    def __bool__(self) -> bool:
        return self._element is not None and bool(str(self))

    def __html__(self) -> str:
        # Jinja calls this instead of escaping; the text is escaped by hand so
        # that document content can never inject markup into the form.
        from markupsafe import escape

        return str(escape(str(self)))


def parse(body: str) -> Node:
    """Parse a document body into a namespace-free tree."""
    root = fromstring(body)
    for element in root.iter():
        if "}" in element.tag:
            element.tag = element.tag.rpartition("}")[2]
    return Node(root)


def act_recipient_tins(body: str) -> set[str]:
    """BINs listed as recipients (customers) of an act."""
    act = parse(body)
    return {str(node.tin) for node in act.recipients.all("recipient") if node.tin}
