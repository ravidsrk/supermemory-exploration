"""SuperServe sandbox lifecycle and command adapter."""

from typing import Any, Mapping, Optional
from urllib.parse import quote

from ..http import JsonObject, JsonTransport, UrlLibTransport
from .query import with_query


class SuperServeClient:
    def __init__(self, transport: JsonTransport) -> None:
        self._transport = transport

    def list_sandboxes(self, *, limit: int = 20) -> JsonObject:
        return self._transport.request("GET", with_query("/sandboxes", {"limit": limit}))

    def create_sandbox(
        self,
        name: str,
        *,
        template: str = "superserve/base",
        timeout_seconds: int = 900,
        metadata: Optional[Mapping[str, str]] = None,
    ) -> JsonObject:
        return self._transport.request(
            "POST",
            "/sandboxes",
            {
                "name": name,
                "from_template": template,
                "timeout_seconds": timeout_seconds,
                "metadata": dict(metadata or {}),
            },
        )

    def delete_sandbox(self, sandbox_id: str) -> JsonObject:
        return self._transport.request(
            "DELETE", f"/sandboxes/{quote(sandbox_id, safe='')}"
        )

    @staticmethod
    def command_transport(sandbox_id: str, access_token: str) -> UrlLibTransport:
        return UrlLibTransport(
            "https://sandbox.superserve.ai",
            access_token,
            timeout_seconds=120,
            auth_header="X-Access-Token",
            auth_scheme=None,
            extra_headers={"X-Superserve-Sandbox-Id": sandbox_id},
        )

    @staticmethod
    def exec(
        command_transport: JsonTransport,
        command: str,
        *,
        working_dir: Optional[str] = None,
        timeout_seconds: int = 30,
        env: Optional[Mapping[str, str]] = None,
    ) -> JsonObject:
        body: JsonObject = {"command": command, "timeout_s": timeout_seconds}
        if working_dir:
            body["working_dir"] = working_dir
        if env:
            body["env"] = dict(env)
        return command_transport.request("POST", "/exec", body)
