"""Composio catalog adapter; execution is intentionally a separate decision."""

from typing import Optional

from ..http import JsonObject, JsonTransport
from .query import with_query


class ComposioClient:
    def __init__(self, transport: JsonTransport) -> None:
        self._transport = transport

    def list_toolkits(self, *, search: Optional[str] = None, limit: int = 10) -> JsonObject:
        return self._transport.request(
            "GET", with_query("/api/v3.1/toolkits", {"search": search, "limit": limit})
        )

    def list_tools(
        self,
        *,
        query: Optional[str] = None,
        toolkit_slug: Optional[str] = None,
        limit: int = 10,
    ) -> JsonObject:
        return self._transport.request(
            "GET",
            with_query(
                "/api/v3/tools",
                {
                    "query": query,
                    "toolkit_slug": toolkit_slug,
                    "toolkit_versions": "latest",
                    "limit": limit,
                },
            ),
        )
