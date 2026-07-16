"""Context.dev brand and web intelligence adapter."""

from ..http import JsonObject, JsonTransport
from .query import with_query


class ContextDevClient:
    def __init__(self, transport: JsonTransport) -> None:
        self._transport = transport

    def brand(self, domain: str, *, max_speed: bool = True) -> JsonObject:
        return self._transport.request(
            "GET",
            with_query(
                "/brand/retrieve", {"domain": domain, "maxSpeed": max_speed}
            ),
        )

    def scrape_markdown(self, url: str, *, max_age_ms: int = 0) -> JsonObject:
        return self._transport.request(
            "POST", "/web/scrape/markdown", {"url": url, "max_age": max_age_ms}
        )
