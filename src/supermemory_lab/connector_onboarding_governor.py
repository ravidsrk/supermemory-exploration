"""Governed OAuth/resource-selection lifecycle for privileged knowledge connectors."""

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import hashlib
import hmac
import json
from typing import Any, Dict, List, Mapping, Protocol, Sequence, Tuple


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


class ConnectorMemory(Protocol):
    def create_connection(self, provider: str, **kwargs: Any) -> Dict[str, Any]:
        ...

    def get_connection(self, connection_id: str) -> Dict[str, Any]:
        ...

    def fetch_connection_resources(self, connection_id: str, **kwargs: Any) -> Dict[str, Any]:
        ...

    def configure_connection_resources(
        self, connection_id: str, resources: Sequence[Mapping[str, Any]]
    ) -> Dict[str, Any]:
        ...

    def delete_connection(
        self, connection_id: str, *, delete_documents: bool = True
    ) -> Dict[str, Any]:
        ...


@dataclass(frozen=True)
class ConnectorIntent:
    provider: str
    container_tags: Tuple[str, ...]
    redirect_url: str
    document_limit: int
    metadata: Mapping[str, Any]
    intent_hash: str
    signature: str


@dataclass(frozen=True)
class ConnectorAuthorization:
    intent_hash: str
    actor: str


@dataclass(frozen=True)
class PendingConnector:
    connection_id: str
    provider: str
    intent_hash: str
    auth_required: bool
    auth_link_hash: str
    created_at: str
    signature: str


@dataclass(frozen=True)
class ConnectorResource:
    resource_id: str
    name_hash: str
    default_branch: str
    private: bool
    raw: Mapping[str, Any]


@dataclass(frozen=True)
class ResourceSnapshot:
    connection_id: str
    intent_hash: str
    resources: Tuple[ConnectorResource, ...]
    resource_digest: str
    captured_at: str
    signature: str


@dataclass(frozen=True)
class ResourcePlan:
    connection_id: str
    intent_hash: str
    resource_digest: str
    selected_resource_ids: Tuple[str, ...]
    selected_payloads: Tuple[Mapping[str, Any], ...]
    plan_hash: str
    signature: str


@dataclass(frozen=True)
class ResourceAuthorization:
    plan_hash: str
    resource_digest: str
    actor: str


class GovernedConnectorOnboarding:
    PROVIDERS = {
        "notion",
        "google-drive",
        "onedrive",
        "gmail",
        "github",
        "web-crawler",
        "s3",
        "granola",
    }

    def __init__(self, memory: ConnectorMemory, *, signing_key: bytes) -> None:
        if len(signing_key) < 16:
            raise ValueError("signing_key must contain at least 16 bytes")
        self._memory = memory
        self._key = signing_key
        self._configured: set = set()

    def _sign(self, value: Any) -> str:
        return hmac.new(
            self._key, _canonical(value).encode("utf-8"), hashlib.sha256
        ).hexdigest()

    def issue_intent(
        self,
        *,
        provider: str,
        container_tags: Sequence[str],
        redirect_url: str,
        document_limit: int,
        metadata: Mapping[str, Any],
    ) -> ConnectorIntent:
        tags = tuple(container_tags)
        if (
            provider not in self.PROVIDERS
            or not tags
            or len(set(tags)) != len(tags)
            or any(not tag.strip() or len(tag) > 100 for tag in tags)
            or not 1 <= document_limit <= 10_000
        ):
            raise ValueError("connector intent scope/provider/limit is invalid")
        if provider != "web-crawler" and not redirect_url.startswith("https://"):
            raise ValueError("OAuth connector redirect must be HTTPS")
        if provider == "web-crawler" and not str(metadata.get("startUrl") or "").startswith(
            "https://"
        ):
            raise ValueError("web crawler requires an HTTPS startUrl")
        payload = {
            "provider": provider,
            "containerTags": tags,
            "redirectUrl": redirect_url,
            "documentLimit": document_limit,
            "metadata": dict(metadata),
        }
        intent_hash = _digest(payload)
        return ConnectorIntent(
            provider,
            tags,
            redirect_url,
            document_limit,
            dict(metadata),
            intent_hash,
            self._sign({"intentHash": intent_hash, **payload}),
        )

    def verify_intent(self, intent: ConnectorIntent) -> bool:
        try:
            rebuilt = self.issue_intent(
                provider=intent.provider,
                container_tags=intent.container_tags,
                redirect_url=intent.redirect_url,
                document_limit=intent.document_limit,
                metadata=intent.metadata,
            )
        except ValueError:
            return False
        return (
            rebuilt.intent_hash == intent.intent_hash
            and hmac.compare_digest(rebuilt.signature, intent.signature)
        )

    def begin(
        self, intent: ConnectorIntent, authorization: ConnectorAuthorization
    ) -> PendingConnector:
        if not self.verify_intent(intent):
            raise PermissionError("connector intent signature is invalid")
        if (
            authorization.intent_hash != intent.intent_hash
            or not authorization.actor.strip()
        ):
            raise PermissionError("connector intent authorization is invalid")
        response = self._memory.create_connection(
            intent.provider,
            container_tags=intent.container_tags,
            redirect_url=intent.redirect_url or None,
            metadata=intent.metadata,
            document_limit=intent.document_limit,
        )
        connection_id = response.get("id")
        if not isinstance(connection_id, str) or not connection_id:
            raise RuntimeError("connection response omitted ID")
        auth_link = response.get("authLink")
        auth_required = isinstance(auth_link, str) and bool(auth_link)
        unsigned = PendingConnector(
            connection_id,
            intent.provider,
            intent.intent_hash,
            auth_required,
            hashlib.sha256(auth_link.encode("utf-8")).hexdigest()
            if auth_required
            else "",
            datetime.now(timezone.utc).isoformat(),
            "",
        )
        return replace(unsigned, signature=self._sign(asdict(unsigned)))

    def verify_pending(self, pending: PendingConnector) -> bool:
        return bool(pending.connection_id) and hmac.compare_digest(
            pending.signature, self._sign(asdict(replace(pending, signature="")))
        )

    def capture_resources(self, pending: PendingConnector) -> ResourceSnapshot:
        if not self.verify_pending(pending):
            raise PermissionError("pending connector signature is invalid")
        if pending.provider != "github":
            raise PermissionError("resource selection is currently governed for GitHub only")
        response = self._memory.fetch_connection_resources(
            pending.connection_id, page=1, per_page=100
        )
        raw_resources = response.get("resources")
        if not isinstance(raw_resources, list):
            raise RuntimeError("resource response omitted resources")
        resources: List[ConnectorResource] = []
        seen = set()
        for raw in raw_resources:
            if not isinstance(raw, Mapping):
                raise RuntimeError("resource response contained a non-object")
            resource_id = str(raw.get("id") or "")
            name = str(raw.get("full_name") or raw.get("name") or "")
            if not resource_id or not name or resource_id in seen:
                raise RuntimeError("resources require unique IDs and names")
            seen.add(resource_id)
            resources.append(
                ConnectorResource(
                    resource_id,
                    hashlib.sha256(name.encode("utf-8")).hexdigest(),
                    str(raw.get("default_branch") or raw.get("defaultBranch") or ""),
                    bool(raw.get("private", False)),
                    dict(raw),
                )
            )
        ordered = tuple(sorted(resources, key=lambda item: item.resource_id))
        digest = _digest(
            [
                {
                    "id": item.resource_id,
                    "nameHash": item.name_hash,
                    "defaultBranch": item.default_branch,
                    "private": item.private,
                }
                for item in ordered
            ]
        )
        unsigned = ResourceSnapshot(
            pending.connection_id,
            pending.intent_hash,
            ordered,
            digest,
            datetime.now(timezone.utc).isoformat(),
            "",
        )
        return replace(unsigned, signature=self._sign(asdict(unsigned)))

    def verify_snapshot(self, snapshot: ResourceSnapshot) -> bool:
        expected_digest = _digest(
            [
                {
                    "id": item.resource_id,
                    "nameHash": item.name_hash,
                    "defaultBranch": item.default_branch,
                    "private": item.private,
                }
                for item in snapshot.resources
            ]
        )
        return (
            snapshot.resource_digest == expected_digest
            and hmac.compare_digest(
                snapshot.signature,
                self._sign(asdict(replace(snapshot, signature=""))),
            )
        )

    def plan(
        self, snapshot: ResourceSnapshot, selected_resource_ids: Sequence[str]
    ) -> ResourcePlan:
        if not self.verify_snapshot(snapshot):
            raise PermissionError("resource snapshot signature is invalid")
        selected = tuple(sorted(set(selected_resource_ids)))
        if not selected or len(selected) != len(selected_resource_ids):
            raise ValueError("resource selection must be non-empty and unique")
        by_id = {item.resource_id: item for item in snapshot.resources}
        if any(resource_id not in by_id for resource_id in selected):
            raise PermissionError("resource selection exceeds captured candidates")
        payloads = tuple(dict(by_id[resource_id].raw) for resource_id in selected)
        payload = {
            "connectionId": snapshot.connection_id,
            "intentHash": snapshot.intent_hash,
            "resourceDigest": snapshot.resource_digest,
            "selectedResourceIds": selected,
            "selectedPayloadHashes": tuple(_digest(value) for value in payloads),
        }
        plan_hash = _digest(payload)
        unsigned = ResourcePlan(
            snapshot.connection_id,
            snapshot.intent_hash,
            snapshot.resource_digest,
            selected,
            payloads,
            plan_hash,
            "",
        )
        return replace(unsigned, signature=self._sign(asdict(unsigned)))

    def verify_plan(self, plan: ResourcePlan) -> bool:
        payload = {
            "connectionId": plan.connection_id,
            "intentHash": plan.intent_hash,
            "resourceDigest": plan.resource_digest,
            "selectedResourceIds": plan.selected_resource_ids,
            "selectedPayloadHashes": tuple(_digest(value) for value in plan.selected_payloads),
        }
        return (
            plan.plan_hash == _digest(payload)
            and hmac.compare_digest(
                plan.signature, self._sign(asdict(replace(plan, signature="")))
            )
        )

    def apply(
        self,
        pending: PendingConnector,
        snapshot: ResourceSnapshot,
        plan: ResourcePlan,
        authorization: ResourceAuthorization,
    ) -> Dict[str, Any]:
        if (
            not self.verify_pending(pending)
            or not self.verify_snapshot(snapshot)
            or not self.verify_plan(plan)
        ):
            raise PermissionError("connector configuration evidence is invalid")
        if (
            pending.connection_id != snapshot.connection_id
            or plan.connection_id != snapshot.connection_id
            or pending.intent_hash != snapshot.intent_hash
            or plan.intent_hash != snapshot.intent_hash
            or plan.resource_digest != snapshot.resource_digest
        ):
            raise PermissionError("connector configuration ancestry is invalid")
        if (
            authorization.plan_hash != plan.plan_hash
            or authorization.resource_digest != snapshot.resource_digest
            or not authorization.actor.strip()
        ):
            raise PermissionError("resource authorization is invalid")
        if plan.plan_hash in self._configured:
            raise RuntimeError("connector configuration replay denied")
        current = self.capture_resources(pending)
        if current.resource_digest != snapshot.resource_digest:
            raise RuntimeError("connector resources changed after selection")
        response = self._memory.configure_connection_resources(
            pending.connection_id, plan.selected_payloads
        )
        if response.get("success") is not True:
            raise RuntimeError("connector resource configuration did not report success")
        self._configured.add(plan.plan_hash)
        return response

    def disconnect_preserving_documents(
        self, pending: PendingConnector, authorization: ConnectorAuthorization
    ) -> Dict[str, Any]:
        if not self.verify_pending(pending):
            raise PermissionError("pending connector signature is invalid")
        if (
            authorization.intent_hash != pending.intent_hash
            or not authorization.actor.strip()
        ):
            raise PermissionError("disconnect authorization is invalid")
        return self._memory.delete_connection(
            pending.connection_id, delete_documents=False
        )
