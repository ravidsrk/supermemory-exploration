"""Exa search and contents adapter."""

from typing import Any, Mapping, Optional, Sequence

from ..http import JsonObject, JsonTransport


class ExaClient:
    def __init__(self, transport: JsonTransport) -> None:
        self._transport = transport

    def search(
        self,
        query: str,
        *,
        num_results: int = 5,
        search_type: str = "auto",
        include_domains: Optional[Sequence[str]] = None,
        highlights: bool = True,
    ) -> JsonObject:
        contents: Mapping[str, Any] = (
            {"highlights": {"maxCharacters": 1_500}} if highlights else {}
        )
        body: JsonObject = {
            "query": query,
            "numResults": num_results,
            "type": search_type,
            "contents": contents,
        }
        if include_domains:
            body["includeDomains"] = list(include_domains)
        return self._transport.request("POST", "/search", body)
