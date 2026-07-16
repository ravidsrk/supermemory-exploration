"""Read-only Vercel operations adapter for release-memory experiments."""

from typing import Optional

from ..http import JsonObject, JsonTransport
from .query import with_query


class VercelClient:
    def __init__(self, transport: JsonTransport) -> None:
        self._transport = transport

    def current_user(self) -> JsonObject:
        return self._transport.request("GET", "/v2/user")

    def list_projects(self, *, limit: int = 20) -> JsonObject:
        return self._transport.request("GET", with_query("/v9/projects", {"limit": limit}))

    def list_deployments(
        self, *, project_id: Optional[str] = None, limit: int = 20
    ) -> JsonObject:
        return self._transport.request(
            "GET",
            with_query("/v6/deployments", {"projectId": project_id, "limit": limit}),
        )
