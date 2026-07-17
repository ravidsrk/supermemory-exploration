"""Checkpointed exact-ID deletion for large imports without broad selectors."""

from dataclasses import asdict, dataclass, replace
import hashlib
import hmac
import json
from typing import Any, Callable, Dict, Optional, Protocol, Sequence, Tuple

from .integrity import canonical_json as _canonical, digest_json as _digest

from .authorization import AuthorizationLedger, consume_authorization
from .http import ApiError



class ExactDeletionMemory(Protocol):
    def bulk_delete_documents(self, document_ids: Sequence[str]) -> Dict[str, Any]:
        ...

    def get_document(self, document_id: str) -> Dict[str, Any]:
        ...


class AmbiguousDeletionError(RuntimeError):
    """Deletion outcome could not be reconciled after a bad acknowledgement."""


@dataclass(frozen=True)
class ExactDeletionPlan:
    container_tag: str
    source_manifest_hash: str
    document_ids: Tuple[str, ...]
    plan_hash: str
    signature: str


@dataclass(frozen=True)
class DeletionAuthorization:
    plan_hash: str
    source_manifest_hash: str
    actor: str


@dataclass(frozen=True)
class DeletionCheckpoint:
    plan_hash: str
    deleted_document_ids: Tuple[str, ...]
    completed_batches: int
    complete: bool
    checkpoint_hash: str
    signature: str


class ExactDeletionController:
    """Deletes only signed IDs, at the hosted maximum of 100 per request."""

    def __init__(
        self,
        memory: ExactDeletionMemory,
        *,
        signing_key: bytes,
        authorization_ledger: AuthorizationLedger,
        checkpoint_sink: Optional[Callable[[DeletionCheckpoint], None]] = None,
    ) -> None:
        if len(signing_key) < 16:
            raise ValueError("signing_key must contain at least 16 bytes")
        self._memory = memory
        self._key = signing_key
        self._authorization_ledger = authorization_ledger
        self._sink = checkpoint_sink or (lambda checkpoint: None)

    def _sign(self, value: Any) -> str:
        return hmac.new(
            self._key, _canonical(value).encode("utf-8"), hashlib.sha256
        ).hexdigest()

    def _confirmed_absent(self, document_ids: Sequence[str]) -> Tuple[str, ...]:
        absent = []
        for document_id in document_ids:
            try:
                self._memory.get_document(document_id)
            except ApiError as error:
                if error.status in {404, 410}:
                    absent.append(document_id)
                    continue
                raise AmbiguousDeletionError(
                    "exact deletion reconciliation failed on a provider error"
                ) from error
            except Exception as error:
                raise AmbiguousDeletionError(
                    "exact deletion reconciliation could not determine document state"
                ) from error
        return tuple(absent)

    def build_plan(
        self,
        *,
        container_tag: str,
        source_manifest_hash: str,
        document_ids: Sequence[str],
    ) -> ExactDeletionPlan:
        normalized = tuple(sorted(str(value).strip() for value in document_ids))
        if (
            not container_tag.strip()
            or not source_manifest_hash.strip()
            or not normalized
            or any(not value for value in normalized)
            or len(set(normalized)) != len(normalized)
        ):
            raise ValueError("deletion plan scope, manifest, and unique IDs are required")
        payload = {
            "containerTag": container_tag,
            "sourceManifestHash": source_manifest_hash,
            "documentIds": normalized,
        }
        plan_hash = _digest(payload)
        return ExactDeletionPlan(
            container_tag,
            source_manifest_hash,
            normalized,
            plan_hash,
            self._sign({"planHash": plan_hash, **payload}),
        )

    def verify_plan(self, plan: ExactDeletionPlan) -> bool:
        try:
            rebuilt = self.build_plan(
                container_tag=plan.container_tag,
                source_manifest_hash=plan.source_manifest_hash,
                document_ids=plan.document_ids,
            )
        except ValueError:
            return False
        return (
            rebuilt.plan_hash == plan.plan_hash
            and hmac.compare_digest(rebuilt.signature, plan.signature)
        )

    def _checkpoint(
        self, plan: ExactDeletionPlan, deleted: Sequence[str], batches: int
    ) -> DeletionCheckpoint:
        normalized = tuple(sorted(set(deleted)))
        unsigned = DeletionCheckpoint(
            plan.plan_hash,
            normalized,
            batches,
            len(normalized) == len(plan.document_ids),
            "",
            "",
        )
        checkpoint_hash = _digest(asdict(unsigned))
        with_hash = replace(unsigned, checkpoint_hash=checkpoint_hash)
        return replace(
            with_hash,
            signature=self._sign(asdict(replace(with_hash, signature=""))),
        )

    def verify_checkpoint(
        self, plan: ExactDeletionPlan, checkpoint: DeletionCheckpoint
    ) -> bool:
        unsigned = replace(checkpoint, checkpoint_hash="", signature="")
        expected_hash = _digest(asdict(unsigned))
        return (
            self.verify_plan(plan)
            and checkpoint.plan_hash == plan.plan_hash
            and set(checkpoint.deleted_document_ids) <= set(plan.document_ids)
            and len(set(checkpoint.deleted_document_ids))
            == len(checkpoint.deleted_document_ids)
            and checkpoint.completed_batches >= 0
            and checkpoint.complete
            == (len(checkpoint.deleted_document_ids) == len(plan.document_ids))
            and checkpoint.checkpoint_hash == expected_hash
            and hmac.compare_digest(
                checkpoint.signature,
                self._sign(asdict(replace(checkpoint, signature=""))),
            )
        )

    def apply(
        self,
        plan: ExactDeletionPlan,
        authorization: DeletionAuthorization,
        *,
        checkpoint: Optional[DeletionCheckpoint] = None,
        max_batches: Optional[int] = None,
    ) -> DeletionCheckpoint:
        if not self.verify_plan(plan):
            raise PermissionError("exact deletion plan signature is invalid")
        if (
            authorization.plan_hash != plan.plan_hash
            or authorization.source_manifest_hash != plan.source_manifest_hash
            or not authorization.actor.strip()
        ):
            raise PermissionError("exact deletion authorization is invalid")
        if checkpoint is not None and not self.verify_checkpoint(plan, checkpoint):
            raise PermissionError("deletion checkpoint is invalid")
        if checkpoint is None:
            consume_authorization(
                self._authorization_ledger,
                scope="exact-deletion.apply",
                actor=authorization.actor,
                resource_hash=plan.plan_hash,
            )
        if max_batches is not None and max_batches < 1:
            raise ValueError("max_batches must be positive")
        deleted = list(checkpoint.deleted_document_ids if checkpoint else ())
        batches = checkpoint.completed_batches if checkpoint else 0
        latest = checkpoint or self._checkpoint(plan, deleted, batches)
        completed_this_call = 0
        pending = [item for item in plan.document_ids if item not in set(deleted)]
        while pending:
            batch = pending[:100]
            try:
                response = self._memory.bulk_delete_documents(batch)
            except Exception:
                confirmed = self._confirmed_absent(batch)
            else:
                errors = response.get("errors")
                acknowledged = (
                    response.get("success") is True
                    and int(response.get("deletedCount") or 0) == len(batch)
                    and not (isinstance(errors, list) and errors)
                )
                confirmed = tuple(batch) if acknowledged else self._confirmed_absent(batch)
            if not confirmed:
                raise AmbiguousDeletionError(
                    "exact bulk deletion was unsuccessful and no absence was confirmed"
                )
            deleted.extend(confirmed)
            batches += 1
            completed_this_call += 1
            latest = self._checkpoint(plan, deleted, batches)
            self._sink(latest)
            pending = [item for item in plan.document_ids if item not in set(deleted)]
            if max_batches is not None and completed_this_call >= max_batches:
                break
        return latest
