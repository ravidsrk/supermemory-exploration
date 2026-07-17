"""Minimal JSON HTTP transport with safe error reporting."""

from dataclasses import dataclass
import json
import secrets
from typing import Any, Dict, Mapping, Optional, Protocol, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


JsonObject = Dict[str, Any]


class JsonTransport(Protocol):
    def request(
        self,
        method: str,
        path: str,
        body: Optional[Mapping[str, Any]] = None,
    ) -> JsonObject:
        ...


class MultipartJsonTransport(JsonTransport, Protocol):
    def request_multipart(
        self,
        method: str,
        path: str,
        *,
        fields: Mapping[str, str],
        files: Mapping[str, Tuple[str, bytes, str]],
    ) -> JsonObject:
        ...


@dataclass
class ApiError(RuntimeError):
    method: str
    path: str
    status: Optional[int]
    detail: str

    def __str__(self) -> str:
        status = str(self.status) if self.status is not None else "network"
        return f"{self.method} {self.path} failed ({status}): {self.detail}"


class UrlLibTransport:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout_seconds: float = 30.0,
        extra_headers: Optional[Mapping[str, str]] = None,
        auth_header: str = "Authorization",
        auth_scheme: Optional[str] = "Bearer",
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._extra_headers = dict(extra_headers or {})
        self._auth_header = auth_header
        self._auth_scheme = auth_scheme

    def request(
        self,
        method: str,
        path: str,
        body: Optional[Mapping[str, Any]] = None,
    ) -> JsonObject:
        encoded = None if body is None else json.dumps(body).encode("utf-8")
        credential = (
            f"{self._auth_scheme} {self._api_key}"
            if self._auth_scheme
            else self._api_key
        )
        headers = {
            "Accept": "application/json",
            self._auth_header: credential,
            "Content-Type": "application/json",
            "User-Agent": "supermemory-field-lab/0.1",
            **self._extra_headers,
        }
        return self._send(method, path, encoded, headers)

    def request_multipart(
        self,
        method: str,
        path: str,
        *,
        fields: Mapping[str, str],
        files: Mapping[str, Tuple[str, bytes, str]],
    ) -> JsonObject:
        """Send a bounded multipart form without logging file or credential contents."""

        boundary = f"supermemory-field-lab-{secrets.token_hex(16)}"
        body = bytearray()
        for name, value in fields.items():
            safe_name = _safe_disposition_value(name)
            body.extend(f"--{boundary}\r\n".encode("ascii"))
            body.extend(
                (
                    f'Content-Disposition: form-data; name="{safe_name}"\r\n\r\n'
                    f"{value}\r\n"
                ).encode("utf-8")
            )
        for name, (filename, content, content_type) in files.items():
            safe_name = _safe_disposition_value(name)
            safe_filename = _safe_disposition_value(filename)
            safe_content_type = content_type.replace("\r", "").replace("\n", "")
            body.extend(f"--{boundary}\r\n".encode("ascii"))
            body.extend(
                (
                    f'Content-Disposition: form-data; name="{safe_name}"; '
                    f'filename="{safe_filename}"\r\n'
                    f"Content-Type: {safe_content_type}\r\n\r\n"
                ).encode("utf-8")
            )
            body.extend(content)
            body.extend(b"\r\n")
        body.extend(f"--{boundary}--\r\n".encode("ascii"))

        credential = (
            f"{self._auth_scheme} {self._api_key}"
            if self._auth_scheme
            else self._api_key
        )
        headers = {
            "Accept": "application/json",
            self._auth_header: credential,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "supermemory-field-lab/0.1",
            **self._extra_headers,
        }
        return self._send(method, path, bytes(body), headers)

    def _send(
        self,
        method: str,
        path: str,
        encoded: Optional[bytes],
        headers: Mapping[str, str],
    ) -> JsonObject:
        request = Request(
            f"{self._base_url}{path}",
            data=encoded,
            headers=dict(headers),
            method=method.upper(),
        )

        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as error:
            raw = error.read().decode("utf-8", errors="replace")
            raise ApiError(
                method.upper(), path, error.code, _safe_error_detail(raw)
            ) from None
        except URLError as error:
            raise ApiError(method.upper(), path, None, str(error.reason)) from None

        if not raw.strip():
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            raise ApiError(
                method.upper(), path, None, "response was not valid JSON"
            ) from None
        if isinstance(parsed, dict):
            return parsed
        return {"data": parsed}


def _safe_disposition_value(value: str) -> str:
    return str(value).replace("\r", "").replace("\n", "").replace('"', "'")


def _safe_error_detail(raw: str) -> str:
    """Extract bounded API error text without including request headers."""

    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            for key in ("message", "error", "detail"):
                value = parsed.get(key)
                if isinstance(value, str):
                    return value[:500]
                if isinstance(value, dict) and isinstance(value.get("message"), str):
                    return value["message"][:500]
    except json.JSONDecodeError:
        pass
    return raw.strip()[:500] or "empty error response"
