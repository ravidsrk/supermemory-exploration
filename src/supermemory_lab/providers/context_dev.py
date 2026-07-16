"""Context.dev brand, web intelligence, and monitor adapter."""

from typing import Optional
from urllib.parse import quote

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
        # The current v1 contract is a GET with the target URL in the query string.
        # Keep the historical argument for callers, but only send the documented URL;
        # the current API does not document a cache-age parameter.
        return self._transport.request(
            "GET", with_query("/web/scrape/markdown", {"url": url})
        )

    def monitor_limits(self) -> JsonObject:
        return self._transport.request("GET", "/monitors/limits")

    def create_page_monitor(
        self,
        *,
        name: str,
        url: str,
        frequency: int = 1,
        unit: str = "days",
        tags: Optional[list] = None,
        normalize_whitespace: bool = True,
    ) -> JsonObject:
        return self._transport.request(
            "POST",
            "/monitors",
            {
                "mode": "web",
                "name": name,
                "tags": list(tags or []),
                "target": {
                    "type": "page",
                    "url": url,
                    "normalize_whitespace": normalize_whitespace,
                },
                "change_detection": {"type": "exact"},
                "schedule": {
                    "type": "interval",
                    "frequency": frequency,
                    "unit": unit,
                },
            },
        )

    def get_monitor(self, monitor_id: str) -> JsonObject:
        return self._transport.request(
            "GET", f"/monitors/{quote(monitor_id, safe='')}"
        )

    def list_monitor_runs(
        self, monitor_id: str, *, status: Optional[str] = None, limit: int = 25
    ) -> JsonObject:
        return self._transport.request(
            "GET",
            with_query(
                f"/monitors/{quote(monitor_id, safe='')}/runs",
                {"status": status, "limit": limit},
            ),
        )

    def list_monitor_changes(self, monitor_id: str, *, limit: int = 25) -> JsonObject:
        return self._transport.request(
            "GET",
            with_query(
                f"/monitors/{quote(monitor_id, safe='')}/changes", {"limit": limit}
            ),
        )

    def run_monitor(self, monitor_id: str) -> JsonObject:
        return self._transport.request(
            "POST", f"/monitors/{quote(monitor_id, safe='')}/run", {}
        )

    def delete_monitor(self, monitor_id: str) -> JsonObject:
        return self._transport.request(
            "DELETE", f"/monitors/{quote(monitor_id, safe='')}"
        )
