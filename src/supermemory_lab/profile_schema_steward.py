"""Additive, snapshot-bound profile bucket schema evolution."""

from dataclasses import asdict, dataclass, replace
import hashlib
import hmac
import json
import re
from typing import Any, Dict, List, Mapping, Protocol, Sequence, Tuple


_KEY = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


class ProfileSchemaMemory(Protocol):
    def get_container_settings(self, container_tag: str) -> Dict[str, Any]:
        ...

    def list_profile_buckets(self, container_tag: str) -> Dict[str, Any]:
        ...

    def update_container_settings(self, container_tag: str, **kwargs: Any) -> Dict[str, Any]:
        ...


@dataclass(frozen=True)
class BucketDefinition:
    key: str
    description: str


@dataclass(frozen=True)
class ProfileSchemaSnapshot:
    container_tag: str
    own_buckets: Tuple[BucketDefinition, ...]
    effective_keys: Tuple[str, ...]
    own_schema_hash: str
    effective_schema_hash: str
    snapshot_hash: str
    signature: str


@dataclass(frozen=True)
class BucketEvolutionPlan:
    container_tag: str
    snapshot_hash: str
    additions: Tuple[BucketDefinition, ...]
    resulting_own_buckets: Tuple[BucketDefinition, ...]
    plan_hash: str
    signature: str


@dataclass(frozen=True)
class BucketEvolutionAuthorization:
    snapshot_hash: str
    plan_hash: str
    actor: str


class GovernedProfileSchemaSteward:
    """Adopts valid bucket suggestions without silently changing or removing current schema."""

    def __init__(
        self,
        memory: ProfileSchemaMemory,
        *,
        container_tag: str,
        signing_key: bytes,
        max_own_buckets: int = 50,
    ) -> None:
        if len(signing_key) < 16:
            raise ValueError("signing_key must contain at least 16 bytes")
        if not 1 <= max_own_buckets <= 50:
            raise ValueError("max_own_buckets must be between 1 and 50")
        self._memory = memory
        self._container_tag = container_tag
        self._key = signing_key
        self._max_own_buckets = max_own_buckets
        self._applied: set[str] = set()

    def _sign(self, value: Any) -> str:
        return hmac.new(
            self._key, _canonical(value).encode("utf-8"), hashlib.sha256
        ).hexdigest()

    @staticmethod
    def _definition(value: Mapping[str, Any]) -> BucketDefinition:
        key = str(value.get("key") or "").strip()
        description = " ".join(str(value.get("description") or "").split())
        if not _KEY.fullmatch(key):
            raise ValueError("bucket key does not match the hosted schema")
        if len(description) > 2_000:
            raise ValueError("bucket description exceeds the hosted schema")
        return BucketDefinition(key, description)

    @classmethod
    def validate_suggestions(
        cls, response: Mapping[str, Any], *, max_suggestions: int = 6
    ) -> Tuple[BucketDefinition, ...]:
        raw = response.get("suggestions")
        if not isinstance(raw, list) or not 1 <= len(raw) <= max_suggestions:
            raise ValueError("bucket suggestions must be a bounded non-empty list")
        values = tuple(cls._definition(item) for item in raw if isinstance(item, Mapping))
        if len(values) != len(raw) or len({item.key for item in values}) != len(values):
            raise ValueError("bucket suggestions contain invalid or duplicate entries")
        return values

    def _parse_own(self, response: Mapping[str, Any]) -> Tuple[BucketDefinition, ...]:
        raw = response.get("profileBuckets")
        if raw is None:
            return ()
        if not isinstance(raw, list) or len(raw) > self._max_own_buckets:
            raise ValueError("container profile bucket schema is invalid")
        values = tuple(
            self._definition(item) for item in raw if isinstance(item, Mapping)
        )
        if len(values) != len(raw) or len({item.key for item in values}) != len(values):
            raise ValueError("container bucket definitions are invalid or duplicate")
        return tuple(sorted(values, key=lambda item: item.key))

    @staticmethod
    def _parse_effective(response: Mapping[str, Any]) -> Tuple[str, ...]:
        raw = response.get("buckets")
        if not isinstance(raw, list):
            raise ValueError("effective bucket response omitted buckets")
        keys: List[str] = []
        for item in raw:
            if not isinstance(item, Mapping):
                raise ValueError("effective bucket entry must be an object")
            key = str(item.get("key") or "").strip()
            if not _KEY.fullmatch(key):
                raise ValueError("effective bucket key is invalid")
            keys.append(key)
        if len(keys) != len(set(keys)):
            raise ValueError("effective bucket keys are duplicated")
        return tuple(sorted(keys))

    def capture(self) -> ProfileSchemaSnapshot:
        settings = self._memory.get_container_settings(self._container_tag)
        effective = self._memory.list_profile_buckets(self._container_tag)
        own = self._parse_own(settings)
        effective_keys = self._parse_effective(effective)
        own_hash = _digest([asdict(item) for item in own])
        effective_hash = _digest(effective_keys)
        payload = {
            "containerTag": self._container_tag,
            "ownBuckets": [asdict(item) for item in own],
            "effectiveKeys": list(effective_keys),
            "ownSchemaHash": own_hash,
            "effectiveSchemaHash": effective_hash,
        }
        snapshot_hash = _digest(payload)
        unsigned = ProfileSchemaSnapshot(
            self._container_tag,
            own,
            effective_keys,
            own_hash,
            effective_hash,
            snapshot_hash,
            "",
        )
        return replace(unsigned, signature=self._sign(asdict(unsigned)))

    def verify_snapshot(self, snapshot: ProfileSchemaSnapshot) -> bool:
        payload = {
            "containerTag": snapshot.container_tag,
            "ownBuckets": [asdict(item) for item in snapshot.own_buckets],
            "effectiveKeys": list(snapshot.effective_keys),
            "ownSchemaHash": snapshot.own_schema_hash,
            "effectiveSchemaHash": snapshot.effective_schema_hash,
        }
        return (
            snapshot.container_tag == self._container_tag
            and snapshot.own_schema_hash
            == _digest([asdict(item) for item in snapshot.own_buckets])
            and snapshot.effective_schema_hash == _digest(snapshot.effective_keys)
            and snapshot.snapshot_hash == _digest(payload)
            and hmac.compare_digest(
                snapshot.signature,
                self._sign(asdict(replace(snapshot, signature=""))),
            )
        )

    def propose(
        self,
        snapshot: ProfileSchemaSnapshot,
        additions: Sequence[Mapping[str, Any]],
    ) -> BucketEvolutionPlan:
        if not self.verify_snapshot(snapshot):
            raise PermissionError("profile schema snapshot is invalid")
        proposed = tuple(self._definition(value) for value in additions)
        if not proposed or len({item.key for item in proposed}) != len(proposed):
            raise ValueError("bucket additions are empty or duplicate")
        own_by_key = {item.key: item for item in snapshot.own_buckets}
        effective = set(snapshot.effective_keys)
        if any(item.key in effective for item in proposed):
            raise ValueError("bucket addition collides with the effective schema")
        resulting = tuple(
            sorted((*own_by_key.values(), *proposed), key=lambda item: item.key)
        )
        if len(resulting) > self._max_own_buckets:
            raise ValueError("resulting bucket schema exceeds its bound")
        payload = {
            "containerTag": self._container_tag,
            "snapshotHash": snapshot.snapshot_hash,
            "additions": [asdict(item) for item in proposed],
            "resultingOwnBuckets": [asdict(item) for item in resulting],
        }
        plan_hash = _digest(payload)
        unsigned = BucketEvolutionPlan(
            self._container_tag,
            snapshot.snapshot_hash,
            proposed,
            resulting,
            plan_hash,
            "",
        )
        return replace(unsigned, signature=self._sign(asdict(unsigned)))

    def verify_plan(self, plan: BucketEvolutionPlan) -> bool:
        payload = {
            "containerTag": plan.container_tag,
            "snapshotHash": plan.snapshot_hash,
            "additions": [asdict(item) for item in plan.additions],
            "resultingOwnBuckets": [asdict(item) for item in plan.resulting_own_buckets],
        }
        return (
            plan.container_tag == self._container_tag
            and plan.plan_hash == _digest(payload)
            and hmac.compare_digest(
                plan.signature, self._sign(asdict(replace(plan, signature="")))
            )
        )

    def apply(
        self,
        snapshot: ProfileSchemaSnapshot,
        plan: BucketEvolutionPlan,
        authorization: BucketEvolutionAuthorization,
    ) -> Dict[str, Any]:
        if not self.verify_snapshot(snapshot) or not self.verify_plan(plan):
            raise PermissionError("signed schema artifacts are invalid")
        if (
            plan.snapshot_hash != snapshot.snapshot_hash
            or authorization.snapshot_hash != snapshot.snapshot_hash
            or authorization.plan_hash != plan.plan_hash
            or not authorization.actor.strip()
        ):
            raise PermissionError("authorization does not match the exact schema plan")
        if plan.plan_hash in self._applied:
            raise RuntimeError("profile schema plan replay denied")
        current = self.capture()
        if (
            current.own_schema_hash != snapshot.own_schema_hash
            or current.effective_schema_hash != snapshot.effective_schema_hash
        ):
            raise RuntimeError("profile schema drifted after plan creation")
        expected_existing = {item.key: item for item in snapshot.own_buckets}
        resulting = {item.key: item for item in plan.resulting_own_buckets}
        if any(resulting.get(key) != value for key, value in expected_existing.items()):
            raise PermissionError("schema plan removes or mutates an existing own bucket")
        response = self._memory.update_container_settings(
            self._container_tag,
            profile_buckets=[asdict(item) for item in plan.resulting_own_buckets],
        )
        after = self.capture()
        actual = {item.key: item for item in after.own_buckets}
        if actual != resulting:
            raise RuntimeError("hosted container schema did not match the approved result")
        self._applied.add(plan.plan_hash)
        return response
