"""Signed correctness, isolation, availability, and latency canaries for memory surfaces."""

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import hashlib
import hmac
import json
import math
import time
from typing import Any, Dict, List, Mapping, Protocol, Sequence, Tuple

from .openrouter import LanguageModel


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


class SLOMemory(Protocol):
    def search_memories(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        ...

    def search_documents(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        ...

    def profile(self, container_tag: str, **kwargs: Any) -> Dict[str, Any]:
        ...


@dataclass(frozen=True)
class CanarySpec:
    name: str
    surface: str
    query: str
    expected_term: str
    forbidden_terms: Tuple[str, ...] = ()


@dataclass(frozen=True)
class SLOPolicy:
    minimum_success_rate: float = 0.99
    maximum_p95_ms: float = 2_000.0
    maximum_leaks: int = 0


@dataclass(frozen=True)
class CanarySample:
    canary_name: str
    surface: str
    round_number: int
    latency_ms: float
    expected_hit: bool
    forbidden_leak: bool
    result_count: int
    error_type: str


@dataclass(frozen=True)
class SurfaceMetric:
    surface: str
    samples: int
    successes: int
    p50_ms: float
    p95_ms: float


@dataclass(frozen=True)
class SignedSLOReport:
    container_tag: str
    created_at: str
    samples: Tuple[CanarySample, ...]
    surface_metrics: Tuple[SurfaceMetric, ...]
    success_rate: float
    p50_ms: float
    p95_ms: float
    leak_count: int
    violations: Tuple[str, ...]
    external_action_authorized: bool
    report_hash: str
    signature: str


class MemorySLOCanaryMonitor:
    SURFACES = {"memories", "hybrid", "documents", "profile"}

    def __init__(
        self,
        memory: SLOMemory,
        llm: LanguageModel,
        *,
        container_tag: str,
        signing_key: bytes,
        clock=time.perf_counter,
    ) -> None:
        if len(signing_key) < 16:
            raise ValueError("signing_key must contain at least 16 bytes")
        if not container_tag.strip():
            raise ValueError("container_tag is required")
        self._memory = memory
        self._llm = llm
        self._container = container_tag
        self._key = signing_key
        self._clock = clock

    def _sign(self, value: Any) -> str:
        return hmac.new(
            self._key, _canonical(value).encode("utf-8"), hashlib.sha256
        ).hexdigest()

    @staticmethod
    def _percentile(values: Sequence[float], percentile: float) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        index = max(0, math.ceil(percentile * len(ordered)) - 1)
        return round(ordered[index], 3)

    @staticmethod
    def _result_count(surface: str, response: Mapping[str, Any]) -> int:
        if surface in {"memories", "hybrid", "documents"}:
            results = response.get("results")
            return len(results) if isinstance(results, list) else 0
        profile = response.get("profile")
        profile = profile if isinstance(profile, Mapping) else {}
        count = sum(
            len(profile.get(key) or [])
            for key in ("static", "dynamic")
            if isinstance(profile.get(key), list)
        )
        buckets = profile.get("buckets")
        if isinstance(buckets, Mapping):
            count += sum(len(value) for value in buckets.values() if isinstance(value, list))
        search = response.get("searchResults")
        if isinstance(search, Mapping) and isinstance(search.get("results"), list):
            count += len(search["results"])
        return count

    def _probe(self, spec: CanarySpec, round_number: int) -> CanarySample:
        started = self._clock()
        response: Mapping[str, Any] = {}
        error_type = ""
        try:
            if spec.surface in {"memories", "hybrid"}:
                response = self._memory.search_memories(
                    spec.query,
                    container_tag=self._container,
                    search_mode=spec.surface,
                    threshold=0.0,
                    limit=10,
                    rerank=False,
                    rewrite_query=False,
                    include={"documents": True},
                )
            elif spec.surface == "documents":
                response = self._memory.search_documents(
                    spec.query,
                    container_tags=[self._container],
                    limit=10,
                    chunk_threshold=0.0,
                    document_threshold=0.0,
                    rerank=False,
                    rewrite_query=False,
                    only_matching_chunks=True,
                )
            elif spec.surface == "profile":
                response = self._memory.profile(
                    self._container,
                    query=spec.query,
                    threshold=0.0,
                    include=["static", "dynamic", "buckets"],
                )
            else:
                raise ValueError(f"unknown canary surface: {spec.surface}")
        except Exception as error:
            error_type = type(error).__name__
        latency_ms = round((self._clock() - started) * 1_000, 3)
        serialized = json.dumps(response, ensure_ascii=False, default=str).casefold()
        return CanarySample(
            spec.name,
            spec.surface,
            round_number,
            latency_ms,
            bool(spec.expected_term)
            and spec.expected_term.casefold() in serialized
            and not error_type,
            any(term and term.casefold() in serialized for term in spec.forbidden_terms),
            self._result_count(spec.surface, response),
            error_type,
        )

    def run(
        self,
        specs: Sequence[CanarySpec],
        *,
        rounds: int,
        policy: SLOPolicy,
    ) -> SignedSLOReport:
        if not specs or rounds < 1:
            raise ValueError("at least one canary and one round are required")
        if (
            not 0.0 <= policy.minimum_success_rate <= 1.0
            or policy.maximum_p95_ms <= 0
            or policy.maximum_leaks < 0
        ):
            raise ValueError("SLO policy is invalid")
        names = [spec.name for spec in specs]
        if len(set(names)) != len(names) or any(not name.strip() for name in names):
            raise ValueError("canary names must be non-empty and unique")
        if any(spec.surface not in self.SURFACES for spec in specs):
            raise ValueError("canary surface is invalid")
        samples = tuple(
            self._probe(spec, round_number)
            for round_number in range(1, rounds + 1)
            for spec in specs
        )
        latencies = [sample.latency_ms for sample in samples]
        successes = sum(
            1
            for sample in samples
            if sample.expected_hit and not sample.forbidden_leak and not sample.error_type
        )
        leak_count = sum(1 for sample in samples if sample.forbidden_leak)
        success_rate = successes / len(samples)
        p50 = self._percentile(latencies, 0.50)
        p95 = self._percentile(latencies, 0.95)
        surface_metrics = []
        for surface in sorted({sample.surface for sample in samples}):
            subset = [sample for sample in samples if sample.surface == surface]
            subset_latencies = [sample.latency_ms for sample in subset]
            surface_metrics.append(
                SurfaceMetric(
                    surface,
                    len(subset),
                    sum(
                        1
                        for sample in subset
                        if sample.expected_hit
                        and not sample.forbidden_leak
                        and not sample.error_type
                    ),
                    self._percentile(subset_latencies, 0.50),
                    self._percentile(subset_latencies, 0.95),
                )
            )
        violations = []
        if success_rate < policy.minimum_success_rate:
            violations.append(
                f"success_rate={success_rate:.4f}<minimum={policy.minimum_success_rate:.4f}"
            )
        if p95 > policy.maximum_p95_ms:
            violations.append(
                f"p95_ms={p95:.3f}>maximum={policy.maximum_p95_ms:.3f}"
            )
        if leak_count > policy.maximum_leaks:
            violations.append(
                f"leak_count={leak_count}>maximum={policy.maximum_leaks}"
            )
        unsigned = SignedSLOReport(
            self._container,
            datetime.now(timezone.utc).isoformat(),
            samples,
            tuple(surface_metrics),
            round(success_rate, 6),
            p50,
            p95,
            leak_count,
            tuple(violations),
            False,
            "",
            "",
        )
        report_hash = _digest(asdict(unsigned))
        with_hash = replace(unsigned, report_hash=report_hash)
        return replace(
            with_hash,
            signature=self._sign(asdict(replace(with_hash, signature=""))),
        )

    def verify_report(self, report: SignedSLOReport) -> bool:
        unsigned = replace(report, report_hash="", signature="")
        expected_hash = _digest(asdict(unsigned))
        expected_signature = self._sign(asdict(replace(report, signature="")))
        return (
            report.container_tag == self._container
            and report.external_action_authorized is False
            and report.report_hash == expected_hash
            and hmac.compare_digest(report.signature, expected_signature)
        )

    def explain(self, report: SignedSLOReport) -> str:
        if not self.verify_report(report):
            raise PermissionError("SLO report signature is invalid")
        envelope = "NO_EXTERNAL_ACTION\n"
        if not report.violations:
            return envelope + "MEMORY_SLO_HEALTHY"
        metrics_only = {
            "successRate": report.success_rate,
            "p50Ms": report.p50_ms,
            "p95Ms": report.p95_ms,
            "leakCount": report.leak_count,
            "violations": list(report.violations),
            "surfaceMetrics": [asdict(item) for item in report.surface_metrics],
            "errorTypes": sorted(
                {sample.error_type for sample in report.samples if sample.error_type}
            ),
        }
        prose = self._llm.complete(
            "Explain these synthetic memory SLO metrics briefly. Raw memory is deliberately "
            "excluded. Recommend investigation, but do not authorize a deployment, deletion, "
            "or other external action.",
            _canonical(metrics_only),
        )
        return envelope + prose.strip()
