"""Monid dynamic-tool marketplace adapter."""

from typing import Any, Mapping

from ..http import JsonObject, JsonTransport


class MonidClient:
    def __init__(self, transport: JsonTransport) -> None:
        self._transport = transport

    def discover(self, query: str, *, limit: int = 5) -> JsonObject:
        return self._transport.request(
            "POST", "/v1/discover", {"query": query, "limit": limit}
        )

    def inspect(self, provider: str, endpoint: str) -> JsonObject:
        return self._transport.request(
            "POST", "/v1/inspect", {"provider": provider, "endpoint": endpoint}
        )

    def run(
        self, provider: str, endpoint: str, tool_input: Mapping[str, Any]
    ) -> JsonObject:
        return self._transport.request(
            "POST",
            "/v1/run",
            {"provider": provider, "endpoint": endpoint, "input": dict(tool_input)},
        )
