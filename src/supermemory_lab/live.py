"""Lazy factories for correctly authenticated, least-privilege live clients."""

from functools import cached_property
from typing import Optional

from .client import SupermemoryClient
from .config import LabConfig
from .http import UrlLibTransport
from .openrouter import OpenRouterClient
from .providers import (
    ComposioClient,
    ContextDevClient,
    ExaClient,
    MonidClient,
    ScrapeCreatorsClient,
    SuperServeClient,
    VercelClient,
)


def _transport(
    base_url: str,
    api_key: Optional[str],
    name: str,
    *,
    auth_header: str = "Authorization",
    auth_scheme: Optional[str] = "Bearer",
    timeout_seconds: float = 60,
) -> UrlLibTransport:
    if not api_key:
        raise RuntimeError(f"{name} is required for this experiment")
    return UrlLibTransport(
        base_url,
        api_key,
        timeout_seconds=timeout_seconds,
        auth_header=auth_header,
        auth_scheme=auth_scheme,
    )


class LiveClients:
    """Construct each provider only when an experiment actually accesses it."""

    def __init__(self, config: LabConfig, *, memory_timeout_seconds: float) -> None:
        self._config = config
        self._memory_timeout_seconds = memory_timeout_seconds

    @cached_property
    def memory(self) -> SupermemoryClient:
        return SupermemoryClient(
            _transport(
                self._config.supermemory_base_url,
                self._config.supermemory_api_key,
                "SUPERMEMORY_API_KEY",
                timeout_seconds=self._memory_timeout_seconds,
            )
        )

    @cached_property
    def llm(self) -> OpenRouterClient:
        return OpenRouterClient(
            _transport(
                self._config.openrouter_base_url,
                self._config.openrouter_api_key,
                "OPENROUTER_API_KEY or OPEN_ROUTER_KEY",
            ),
            model=self._config.openrouter_model,
            max_tokens=1_000,
        )

    @cached_property
    def exa(self) -> ExaClient:
        return ExaClient(
            _transport(
                "https://api.exa.ai",
                self._config.exa_api_key,
                "EXA_API_KEY",
                auth_header="x-api-key",
                auth_scheme=None,
            )
        )

    @cached_property
    def context(self) -> ContextDevClient:
        return ContextDevClient(
            _transport(
                "https://api.context.dev/v1",
                self._config.context_dev_api_key,
                "CONTEXT_DEV_API_KEY",
            )
        )

    @cached_property
    def social(self) -> ScrapeCreatorsClient:
        return ScrapeCreatorsClient(
            _transport(
                "https://api.scrapecreators.com",
                self._config.scrapecreators_api_key,
                "SCRAPECREATORS_API_KEY",
                auth_header="x-api-key",
                auth_scheme=None,
            )
        )

    @cached_property
    def monid(self) -> MonidClient:
        return MonidClient(
            _transport(
                "https://api.monid.ai", self._config.monid_api_key, "MONID_API_KEY"
            )
        )

    @cached_property
    def composio(self) -> ComposioClient:
        return ComposioClient(
            _transport(
                "https://backend.composio.dev",
                self._config.composio_api_key,
                "COMPOSIO_API_KEY",
                auth_header="x-api-key",
                auth_scheme=None,
            )
        )

    @cached_property
    def superserve(self) -> SuperServeClient:
        return SuperServeClient(
            _transport(
                "https://api.superserve.ai",
                self._config.superserve_api_key,
                "SUPERSERVE_API_KEY",
                auth_header="X-API-Key",
                auth_scheme=None,
                timeout_seconds=120,
            )
        )

    @cached_property
    def vercel(self) -> VercelClient:
        return VercelClient(
            _transport(
                "https://api.vercel.com", self._config.vercel_token, "VERCEL_TOKEN"
            )
        )


def build_live_clients(
    config: LabConfig, *, memory_timeout_seconds: float = 60
) -> LiveClients:
    return LiveClients(config, memory_timeout_seconds=memory_timeout_seconds)
