"""Query-string construction shared by provider adapters."""

from typing import Any, Mapping
from urllib.parse import urlencode


def with_query(path: str, values: Mapping[str, Any]) -> str:
    query = urlencode(
        {
            key: str(value).lower() if isinstance(value, bool) else value
            for key, value in values.items()
            if value is not None
        },
        doseq=True,
    )
    return f"{path}?{query}" if query else path
