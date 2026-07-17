"""Configuration loading that never logs or serializes credentials."""

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Dict, Optional

from .redaction import register_secrets


@dataclass(frozen=True)
class LabConfig:
    supermemory_api_key: str = field(repr=False)
    openrouter_api_key: Optional[str] = field(default=None, repr=False)
    exa_api_key: Optional[str] = field(default=None, repr=False)
    composio_api_key: Optional[str] = field(default=None, repr=False)
    context_dev_api_key: Optional[str] = field(default=None, repr=False)
    scrapecreators_api_key: Optional[str] = field(default=None, repr=False)
    superserve_api_key: Optional[str] = field(default=None, repr=False)
    monid_api_key: Optional[str] = field(default=None, repr=False)
    vercel_token: Optional[str] = field(default=None, repr=False)
    supermemory_base_url: str = "https://api.supermemory.ai"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "openai/gpt-4.1-mini"


def _read_env_file(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_config(env_file: str = ".env.local") -> LabConfig:
    """Load process variables first, then an ignored local env file.

    The returned dataclass intentionally has no helper that renders its values.
    Callers should report only whether a key is configured, never the key itself.
    """

    file_values = _read_env_file(Path(env_file))

    def value(name: str, fallback: Optional[str] = None) -> Optional[str]:
        return os.environ.get(name) or file_values.get(name) or fallback

    supermemory_key = value("SUPERMEMORY_API_KEY")
    if not supermemory_key:
        raise RuntimeError(
            "SUPERMEMORY_API_KEY is required; set it in the environment or .env.local"
        )

    openrouter_key = value("OPENROUTER_API_KEY") or value("OPEN_ROUTER_KEY")
    config = LabConfig(
        supermemory_api_key=supermemory_key,
        openrouter_api_key=openrouter_key,
        exa_api_key=value("EXA_API_KEY"),
        composio_api_key=value("COMPOSIO_API_KEY"),
        context_dev_api_key=value("CONTEXT_DEV_API_KEY"),
        scrapecreators_api_key=value("SCRAPECREATORS_API_KEY"),
        superserve_api_key=value("SUPERSERVE_API_KEY"),
        monid_api_key=value("MONID_API_KEY"),
        vercel_token=value("VERCEL_TOKEN"),
        supermemory_base_url=value(
            "SUPERMEMORY_BASE_URL", "https://api.supermemory.ai"
        )
        or "https://api.supermemory.ai",
        openrouter_base_url=value(
            "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
        )
        or "https://openrouter.ai/api/v1",
        openrouter_model=value("OPENROUTER_MODEL", "openai/gpt-4.1-mini")
        or "openai/gpt-4.1-mini",
    )
    register_secrets(
        (
            config.supermemory_api_key,
            config.openrouter_api_key,
            config.exa_api_key,
            config.composio_api_key,
            config.context_dev_api_key,
            config.scrapecreators_api_key,
            config.superserve_api_key,
            config.monid_api_key,
            config.vercel_token,
        )
    )
    return config
