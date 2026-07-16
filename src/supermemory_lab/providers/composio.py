"""Composio catalog and explicit tool-execution adapter."""

from typing import Any, Mapping, Optional

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

    def get_tool(self, tool_slug: str) -> JsonObject:
        return self._transport.request(
            "GET",
            with_query(
                f"/api/v3/tools/{tool_slug}", {"toolkit_versions": "latest"}
            ),
        )

    def execute_tool(
        self,
        tool_slug: str,
        *,
        user_id: str,
        arguments: Mapping[str, Any],
        version: str = "latest",
    ) -> JsonObject:
        """Execute after the caller has made an explicit authorization decision."""

        return self._transport.request(
            "POST",
            f"/api/v3/tools/execute/{tool_slug}",
            {
                "user_id": user_id,
                "version": version,
                "arguments": dict(arguments),
            },
        )
