"""Secret-safe, structured traces for multi-provider agent experiments."""

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Any, Callable, Dict, Iterator, List, Mapping, Optional

from .redaction import redact


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunTrace:
    def __init__(self, run_id: str, *, experiment: str) -> None:
        self.run_id = run_id
        self.report: Dict[str, Any] = {
            "schemaVersion": 1,
            "runId": run_id,
            "experiment": experiment,
            "startedAt": utc_now(),
            "steps": [],
            "metrics": {},
        }

    def capture(
        self,
        name: str,
        provider: str,
        action: Callable[[], Any],
        *,
        summarize: Optional[Callable[[Any], Any]] = None,
    ) -> Any:
        started = time.perf_counter()
        try:
            raw = action()
            result = summarize(raw) if summarize else raw
            self._append(name, provider, "ok", started, result=result)
            return raw
        except Exception as error:
            self._append(
                name,
                provider,
                "error",
                started,
                error={"type": type(error).__name__, "message": str(error)},
            )
            raise

    @contextmanager
    def span(self, name: str, provider: str) -> Iterator[Dict[str, Any]]:
        started = time.perf_counter()
        summary: Dict[str, Any] = {}
        try:
            yield summary
            self._append(name, provider, "ok", started, result=summary)
        except Exception as error:
            self._append(
                name,
                provider,
                "error",
                started,
                error={"type": type(error).__name__, "message": str(error)},
            )
            raise

    def metric(self, name: str, value: Any) -> None:
        self.report["metrics"][name] = redact(value, name)

    def _append(
        self,
        name: str,
        provider: str,
        status: str,
        started: float,
        *,
        result: Any = None,
        error: Any = None,
    ) -> None:
        step: Dict[str, Any] = {
            "name": name,
            "provider": provider,
            "status": status,
            "wallTimeMs": round((time.perf_counter() - started) * 1000, 1),
        }
        if result is not None:
            step["result"] = redact(result)
        if error is not None:
            step["error"] = redact(error)
        steps: List[Dict[str, Any]] = self.report["steps"]
        steps.append(step)

    def write(self, directory: str = ".runs") -> Path:
        self.report["finishedAt"] = utc_now()
        output = Path(directory)
        output.mkdir(parents=True, exist_ok=True)
        path = output / f"{self.run_id}.json"
        path.write_text(
            json.dumps(redact(self.report), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return path
