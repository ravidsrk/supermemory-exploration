"""Bounded concurrent correctness and latency challenges across memory read surfaces."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import hashlib
import hmac
import json
import math
import threading
import time
from typing import Any, Dict, List, Mapping, Protocol, Sequence, Tuple

from .integrity import canonical_json as _canonical, digest_json as _digest



class RecallMemory(Protocol):
    def search_memories(self, query: str, **kwargs: Any) -> Dict[str, Any]: ...

    def search_documents(self, query: str, **kwargs: Any) -> Dict[str, Any]: ...

    def profile(self, container_tag: str, **kwargs: Any) -> Dict[str, Any]: ...


@dataclass(frozen=True)
class RecallProbe:
    name: str
    surface: str
    query: str
    expected_term: str
    forbidden_terms: Tuple[str, ...] = ()


@dataclass(frozen=True)
class SignedRecallChallenge:
    container_tag: str
    probes: Tuple[RecallProbe, ...]
    rounds: int
    max_workers: int
    challenge_hash: str
    signature: str


@dataclass(frozen=True)
class RecallSample:
    probe_name: str
    surface: str
    round_number: int
    latency_ms: float
    expected_hit: bool
    forbidden_leak: bool
    result_count: int
    error_type: str


@dataclass(frozen=True)
class RecallSurfaceMetric:
    surface: str
    samples: int
    successes: int
    p50_ms: float
    p95_ms: float
    maximum_ms: float


@dataclass(frozen=True)
class SignedRecallLoadReport:
    challenge_hash: str
    created_at: str
    samples: Tuple[RecallSample, ...]
    surface_metrics: Tuple[RecallSurfaceMetric, ...]
    peak_in_flight: int
    wall_time_ms: float
    requests_per_second: float
    success_rate: float
    leak_count: int
    error_count: int
    external_action_authorized: bool
    report_hash: str
    signature: str


class ConcurrentRecallChallenger:
    SURFACES = {"memories", "hybrid", "documents", "profile"}

    def __init__(
        self,
        memory: RecallMemory,
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

    def build_challenge(
        self,
        probes: Sequence[RecallProbe],
        *,
        rounds: int,
        max_workers: int,
    ) -> SignedRecallChallenge:
        if not probes:
            raise ValueError("at least one recall probe is required")
        if not 1 <= rounds <= 100:
            raise ValueError("rounds must be between 1 and 100")
        if not 1 <= max_workers <= 32:
            raise ValueError("max_workers must be between 1 and 32")
        if len(probes) * rounds > 1_000:
            raise ValueError("challenge cannot exceed 1,000 requests")
        names = [probe.name.strip() for probe in probes]
        if any(not value for value in names) or len(set(names)) != len(names):
            raise ValueError("probe names must be non-empty and unique")
        if any(
            probe.surface not in self.SURFACES
            or not probe.query.strip()
            or not probe.expected_term.strip()
            for probe in probes
        ):
            raise ValueError("probe surface, query, and expected term are required")
        ordered = tuple(sorted(probes, key=lambda item: item.name))
        payload = {
            "containerTag": self._container,
            "probes": [asdict(probe) for probe in ordered],
            "rounds": rounds,
            "maxWorkers": max_workers,
        }
        challenge_hash = _digest(payload)
        return SignedRecallChallenge(
            self._container,
            ordered,
            rounds,
            max_workers,
            challenge_hash,
            self._sign({"challengeHash": challenge_hash, **payload}),
        )

    def verify_challenge(self, challenge: SignedRecallChallenge) -> bool:
        try:
            rebuilt = self.build_challenge(
                challenge.probes,
                rounds=challenge.rounds,
                max_workers=challenge.max_workers,
            )
        except ValueError:
            return False
        return (
            challenge.container_tag == self._container
            and challenge.challenge_hash == rebuilt.challenge_hash
            and hmac.compare_digest(challenge.signature, rebuilt.signature)
        )

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

    def _probe(self, probe: RecallProbe, round_number: int) -> RecallSample:
        started = self._clock()
        response: Mapping[str, Any] = {}
        error_type = ""
        try:
            if probe.surface in {"memories", "hybrid"}:
                response = self._memory.search_memories(
                    probe.query,
                    container_tag=self._container,
                    search_mode=probe.surface,
                    threshold=0.0,
                    limit=10,
                    rerank=False,
                    rewrite_query=False,
                    include={"documents": True},
                )
            elif probe.surface == "documents":
                response = self._memory.search_documents(
                    probe.query,
                    container_tags=[self._container],
                    limit=10,
                    chunk_threshold=0.0,
                    document_threshold=0.0,
                    rerank=False,
                    rewrite_query=False,
                    only_matching_chunks=True,
                )
            else:
                response = self._memory.profile(
                    self._container,
                    query=probe.query,
                    threshold=0.0,
                    include=["static", "dynamic", "buckets"],
                )
        except Exception as error:
            error_type = type(error).__name__
        latency = round((self._clock() - started) * 1_000, 3)
        serialized = json.dumps(response, ensure_ascii=False, default=str).casefold()
        return RecallSample(
            probe.name,
            probe.surface,
            round_number,
            latency,
            probe.expected_term.casefold() in serialized and not error_type,
            any(
                term and term.casefold() in serialized for term in probe.forbidden_terms
            ),
            self._result_count(probe.surface, response),
            error_type,
        )

    def run(self, challenge: SignedRecallChallenge) -> SignedRecallLoadReport:
        if not self.verify_challenge(challenge):
            raise PermissionError("recall challenge signature is invalid")
        counter_lock = threading.Lock()
        in_flight = 0
        peak_in_flight = 0

        def execute(probe: RecallProbe, round_number: int) -> RecallSample:
            nonlocal in_flight, peak_in_flight
            with counter_lock:
                in_flight += 1
                peak_in_flight = max(peak_in_flight, in_flight)
            try:
                return self._probe(probe, round_number)
            finally:
                with counter_lock:
                    in_flight -= 1

        started = self._clock()
        samples: List[RecallSample] = []
        with ThreadPoolExecutor(max_workers=challenge.max_workers) as executor:
            futures = [
                executor.submit(execute, probe, round_number)
                for round_number in range(1, challenge.rounds + 1)
                for probe in challenge.probes
            ]
            for future in as_completed(futures):
                samples.append(future.result())
        wall_time_ms = round((self._clock() - started) * 1_000, 3)
        ordered_samples = tuple(
            sorted(samples, key=lambda item: (item.round_number, item.probe_name))
        )
        success_count = sum(
            1
            for sample in ordered_samples
            if sample.expected_hit and not sample.forbidden_leak and not sample.error_type
        )
        leak_count = sum(1 for sample in ordered_samples if sample.forbidden_leak)
        error_count = sum(1 for sample in ordered_samples if sample.error_type)
        metrics = []
        for surface in sorted({sample.surface for sample in ordered_samples}):
            subset = [sample for sample in ordered_samples if sample.surface == surface]
            latencies = [sample.latency_ms for sample in subset]
            metrics.append(
                RecallSurfaceMetric(
                    surface,
                    len(subset),
                    sum(
                        1
                        for sample in subset
                        if sample.expected_hit
                        and not sample.forbidden_leak
                        and not sample.error_type
                    ),
                    self._percentile(latencies, 0.50),
                    self._percentile(latencies, 0.95),
                    round(max(latencies), 3),
                )
            )
        unsigned = SignedRecallLoadReport(
            challenge.challenge_hash,
            datetime.now(timezone.utc).isoformat(),
            ordered_samples,
            tuple(metrics),
            peak_in_flight,
            wall_time_ms,
            round(len(ordered_samples) / max(wall_time_ms / 1_000, 0.001), 3),
            round(success_count / len(ordered_samples), 6),
            leak_count,
            error_count,
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

    def verify_report(
        self, challenge: SignedRecallChallenge, report: SignedRecallLoadReport
    ) -> bool:
        unsigned = replace(report, report_hash="", signature="")
        expected_hash = _digest(asdict(unsigned))
        return (
            self.verify_challenge(challenge)
            and report.challenge_hash == challenge.challenge_hash
            and len(report.samples) == len(challenge.probes) * challenge.rounds
            and report.peak_in_flight <= challenge.max_workers
            and report.external_action_authorized is False
            and report.report_hash == expected_hash
            and hmac.compare_digest(
                report.signature,
                self._sign(asdict(replace(report, signature=""))),
            )
        )
