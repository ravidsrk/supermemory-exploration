"""Factories for correctly authenticated live clients."""

from dataclasses import dataclass
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


@dataclass(frozen=True)
class LiveClients:
    memory: SupermemoryClient
    llm: OpenRouterClient
    exa: ExaClient
    context: ContextDevClient
    social: ScrapeCreatorsClient
    monid: MonidClient
    composio: ComposioClient
    superserve: SuperServeClient
    vercel: VercelClient


def build_live_clients(
    config: LabConfig, *, memory_timeout_seconds: float = 60
) -> LiveClients:
    return LiveClients(
        memory=SupermemoryClient(
            _transport(
                config.supermemory_base_url,
                config.supermemory_api_key,
                "SUPERMEMORY_API_KEY",
                timeout_seconds=memory_timeout_seconds,
            )
        ),
        llm=OpenRouterClient(
            _transport(
                config.openrouter_base_url,
                config.openrouter_api_key,
                "OPENROUTER_API_KEY or OPEN_ROUTER_KEY",
            ),
            model=config.openrouter_model,
            max_tokens=1_000,
        ),
        exa=ExaClient(
            _transport(
                "https://api.exa.ai",
                config.exa_api_key,
                "EXA_API_KEY",
                auth_header="x-api-key",
                auth_scheme=None,
            )
        ),
        context=ContextDevClient(
            _transport(
                "https://api.context.dev/v1",
                config.context_dev_api_key,
                "CONTEXT_DEV_API_KEY",
            )
        ),
        social=ScrapeCreatorsClient(
            _transport(
                "https://api.scrapecreators.com",
                config.scrapecreators_api_key,
                "SCRAPECREATORS_API_KEY",
                auth_header="x-api-key",
                auth_scheme=None,
            )
        ),
        monid=MonidClient(
            _transport(
                "https://api.monid.ai", config.monid_api_key, "MONID_API_KEY"
            )
        ),
        composio=ComposioClient(
            _transport(
                "https://backend.composio.dev",
                config.composio_api_key,
                "COMPOSIO_API_KEY",
                auth_header="x-api-key",
                auth_scheme=None,
            )
        ),
        superserve=SuperServeClient(
            _transport(
                "https://api.superserve.ai",
                config.superserve_api_key,
                "SUPERSERVE_API_KEY",
                auth_header="X-API-Key",
                auth_scheme=None,
                timeout_seconds=120,
            )
        ),
        vercel=VercelClient(
            _transport(
                "https://api.vercel.com", config.vercel_token, "VERCEL_TOKEN"
            )
        ),
    )
