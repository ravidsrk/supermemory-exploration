"""Adaptive, resumable bulk ingestion with signed checkpoints and exact reconciliation."""

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import hmac
import json
import time
from typing import Any, Callable, Dict, List, Mapping, Optional, Protocol, Sequence, Tuple

from .integrity import canonical_json as _canonical, digest_json as _digest

from .http import ApiError



def _items(value: Any) -> List[Mapping[str, Any]]:
    return [item for item in value or [] if isinstance(item, Mapping)]


class BulkIngestionMemory(Protocol):
    def add_documents_batch(
        self, documents: Sequence[Mapping[str, Any]], **kwargs: Any
    ) -> Dict[str, Any]:
        ...

    def list_documents(self, **kwargs: Any) -> Dict[str, Any]:
        ...

    def get_processing_documents(self, **kwargs: Any) -> Dict[str, Any]:
        ...


@dataclass(frozen=True)
class IngestionRecord:
    custom_id: str
    content: str
    metadata: Mapping[str, Any]

    @property
    def source_hash(self) -> str:
        return hashlib.sha256(self.content.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SignedIngestionManifest:
    run_id: str
    container_tag: str
    records: Tuple[IngestionRecord, ...]
    manifest_hash: str
    signature: str


@dataclass(frozen=True)
class IngestionCheckpoint:
    run_id: str
    manifest_hash: str
    accepted_custom_ids: Tuple[str, ...]
    document_ids: Tuple[str, ...]
    next_batch_size: int
    request_attempts: int
    throttle_events: int
    complete: bool
    checkpoint_hash: str
    signature: str


@dataclass(frozen=True)
class IngestionReport:
    run_id: str
    expected_count: int
    imported_count: int
    done_count: int
    processing_count: int
    failed_count: int
    missing_custom_ids: Tuple[str, ...]
    duplicate_custom_ids: Tuple[str, ...]
    hash_mismatch_custom_ids: Tuple[str, ...]
    unexpected_custom_ids: Tuple[str, ...]
    exact_inventory: bool
    semantically_ready: bool


class AdaptiveBulkIngestionController:
    """Uses stable IDs, additive increase/multiplicative decrease, and no model authority."""

    def __init__(
        self,
        memory: BulkIngestionMemory,
        *,
        container_tag: str,
        run_id: str,
        signing_key: bytes,
        initial_batch_size: int = 50,
        maximum_batch_size: int = 100,
        max_throttle_retries: int = 5,
        ambiguous_recovery_attempts: int = 5,
        sleep: Callable[[float], None] = time.sleep,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        checkpoint_sink: Optional[Callable[[IngestionCheckpoint], None]] = None,
    ) -> None:
        if len(signing_key) < 16:
            raise ValueError("signing_key must contain at least 16 bytes")
        if not run_id.strip() or not container_tag.strip():
            raise ValueError("run and container identifiers are required")
        if not 1 <= initial_batch_size <= maximum_batch_size <= 600:
            raise ValueError("batch sizes must satisfy 1 <= initial <= maximum <= 600")
        if max_throttle_retries < 0:
            raise ValueError("max_throttle_retries cannot be negative")
        if ambiguous_recovery_attempts < 1:
            raise ValueError("ambiguous_recovery_attempts must be positive")
        self._memory = memory
        self._container = container_tag
        self._run_id = run_id
        self._key = signing_key
        self._initial_batch = initial_batch_size
        self._maximum_batch = maximum_batch_size
        self._max_throttle_retries = max_throttle_retries
        self._ambiguous_recovery_attempts = ambiguous_recovery_attempts
        self._sleep = sleep
        self._now = now
        self._sink = checkpoint_sink or (lambda checkpoint: None)

    def _sign(self, value: Any) -> str:
        return hmac.new(
            self._key, _canonical(value).encode("utf-8"), hashlib.sha256
        ).hexdigest()

    def build_manifest(
        self, records: Sequence[IngestionRecord]
    ) -> SignedIngestionManifest:
        if not 1 <= len(records) <= 10_000:
            raise ValueError("ingestion manifest must contain between 1 and 10,000 records")
        custom_ids = [record.custom_id.strip() for record in records]
        if any(not value for value in custom_ids) or len(set(custom_ids)) != len(custom_ids):
            raise ValueError("ingestion custom IDs must be non-empty and unique")
        if any(not record.content.strip() for record in records):
            raise ValueError("ingestion content must be non-empty")
        ordered = tuple(sorted(records, key=lambda item: item.custom_id))
        payload = {
            "runId": self._run_id,
            "containerTag": self._container,
            "records": [
                {
                    "customId": item.custom_id,
                    "sourceHash": item.source_hash,
                    "metadata": dict(item.metadata),
                }
                for item in ordered
            ],
        }
        manifest_hash = _digest(payload)
        return SignedIngestionManifest(
            self._run_id,
            self._container,
            ordered,
            manifest_hash,
            self._sign({"manifestHash": manifest_hash, **payload}),
        )

    def verify_manifest(self, manifest: SignedIngestionManifest) -> bool:
        rebuilt = self.build_manifest(manifest.records)
        return (
            manifest.run_id == self._run_id
            and manifest.container_tag == self._container
            and manifest.manifest_hash == rebuilt.manifest_hash
            and hmac.compare_digest(manifest.signature, rebuilt.signature)
        )

    def _checkpoint(
        self,
        manifest: SignedIngestionManifest,
        *,
        accepted: Sequence[str],
        document_ids: Sequence[str],
        batch_size: int,
        attempts: int,
        throttles: int,
    ) -> IngestionCheckpoint:
        unsigned = IngestionCheckpoint(
            self._run_id,
            manifest.manifest_hash,
            tuple(sorted(set(accepted))),
            tuple(sorted(set(document_ids))),
            batch_size,
            attempts,
            throttles,
            len(set(accepted)) == len(manifest.records),
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
        self, manifest: SignedIngestionManifest, checkpoint: IngestionCheckpoint
    ) -> bool:
        unsigned = replace(checkpoint, checkpoint_hash="", signature="")
        expected_hash = _digest(asdict(unsigned))
        expected_signature = self._sign(asdict(replace(checkpoint, signature="")))
        manifest_ids = {item.custom_id for item in manifest.records}
        return (
            self.verify_manifest(manifest)
            and checkpoint.run_id == self._run_id
            and checkpoint.manifest_hash == manifest.manifest_hash
            and set(checkpoint.accepted_custom_ids) <= manifest_ids
            and len(set(checkpoint.accepted_custom_ids))
            == len(checkpoint.accepted_custom_ids)
            and len(set(checkpoint.document_ids)) == len(checkpoint.document_ids)
            and len(checkpoint.document_ids) == len(checkpoint.accepted_custom_ids)
            and checkpoint.complete
            == (len(checkpoint.accepted_custom_ids) == len(manifest.records))
            and 1 <= checkpoint.next_batch_size <= self._maximum_batch
            and checkpoint.checkpoint_hash == expected_hash
            and hmac.compare_digest(checkpoint.signature, expected_signature)
        )

    def _retry_seconds(self, retry_after: Optional[str]) -> float:
        if retry_after:
            try:
                return min(120.0, max(0.0, float(retry_after)))
            except ValueError:
                try:
                    parsed = parsedate_to_datetime(retry_after)
                    now = self._now()
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    return min(120.0, max(0.0, (parsed - now).total_seconds()))
                except (TypeError, ValueError, OverflowError):
                    pass
        return 1.0

    def _inventory_documents(self) -> List[Mapping[str, Any]]:
        documents: List[Mapping[str, Any]] = []
        seen_inventory_ids = set()
        for page in range(1, 101):
            inventory = self._memory.list_documents(
                container_tags=[self._container], limit=100, page=page
            )
            page_documents = _items(
                inventory.get("documents")
                or inventory.get("memories")
                or inventory.get("results")
            )
            new_documents = []
            for document in page_documents:
                identity = str(document.get("id") or document.get("customId") or "")
                if identity and identity not in seen_inventory_ids:
                    seen_inventory_ids.add(identity)
                    new_documents.append(document)
            documents.extend(new_documents)
            pagination = inventory.get("pagination")
            total_pages = (
                int(pagination.get("totalPages") or 0)
                if isinstance(pagination, Mapping)
                else 0
            )
            if (
                not page_documents
                or not new_documents
                or len(page_documents) < 100
                or (total_pages and page >= total_pages)
            ):
                break
        return documents

    def _recover_ambiguous_batch(
        self, batch: Sequence[IngestionRecord]
    ) -> Optional[List[str]]:
        """Recover a lost acknowledgement only from exact provider inventory.

        A transport timeout after POST has unknown write status. Stable custom IDs,
        run metadata, source hashes, and provider document IDs jointly prove whether
        the complete batch landed. No request is retried when that proof is absent.
        """

        expected = {item.custom_id: item for item in batch}
        last_grouped: Dict[str, List[Tuple[str, Mapping[str, Any]]]] = {}
        for attempt in range(self._ambiguous_recovery_attempts):
            grouped: Dict[str, List[Tuple[str, Mapping[str, Any]]]] = {}
            for document in self._inventory_documents():
                metadata = document.get("metadata")
                metadata = metadata if isinstance(metadata, Mapping) else {}
                if metadata.get("ingestionRunId") != self._run_id:
                    continue
                custom_id = str(
                    document.get("customId") or metadata.get("sourceCustomId") or ""
                )
                if custom_id not in expected:
                    continue
                document_id = str(document.get("id") or "")
                grouped.setdefault(custom_id, []).append((document_id, metadata))
            exact = len(grouped) == len(expected) and all(
                len(grouped[item.custom_id]) == 1
                and bool(grouped[item.custom_id][0][0])
                and grouped[item.custom_id][0][1].get("sourceHash")
                == item.source_hash
                for item in batch
            )
            if exact:
                return [grouped[item.custom_id][0][0] for item in batch]
            last_grouped = grouped
            if attempt + 1 < self._ambiguous_recovery_attempts:
                self._sleep(1.0)
        if last_grouped:
            raise RuntimeError(
                "ambiguous batch write was partial, duplicated, or hash-mismatched"
            )
        return None

    def submit(
        self,
        manifest: SignedIngestionManifest,
        *,
        checkpoint: Optional[IngestionCheckpoint] = None,
        max_accepted_batches: Optional[int] = None,
    ) -> IngestionCheckpoint:
        if not self.verify_manifest(manifest):
            raise PermissionError("ingestion manifest signature is invalid")
        if max_accepted_batches is not None and max_accepted_batches < 1:
            raise ValueError("max_accepted_batches must be positive")
        if checkpoint is not None and not self.verify_checkpoint(manifest, checkpoint):
            raise PermissionError("ingestion checkpoint is invalid")
        accepted = list(checkpoint.accepted_custom_ids if checkpoint else ())
        document_ids = list(checkpoint.document_ids if checkpoint else ())
        batch_size = checkpoint.next_batch_size if checkpoint else self._initial_batch
        attempts = checkpoint.request_attempts if checkpoint else 0
        throttles = checkpoint.throttle_events if checkpoint else 0
        accepted_batches = 0
        throttle_retries = 0
        accepted_set = set(accepted)
        pending = [item for item in manifest.records if item.custom_id not in accepted_set]
        latest = checkpoint or self._checkpoint(
            manifest,
            accepted=accepted,
            document_ids=document_ids,
            batch_size=batch_size,
            attempts=attempts,
            throttles=throttles,
        )
        while pending:
            batch = pending[:batch_size]
            documents = []
            for item in batch:
                metadata = dict(item.metadata)
                metadata.update(
                    {
                        "ingestionRunId": self._run_id,
                        "sourceCustomId": item.custom_id,
                        "sourceHash": item.source_hash,
                    }
                )
                documents.append(
                    {
                        "customId": item.custom_id,
                        "content": item.content,
                        "metadata": metadata,
                    }
                )
            attempts += 1
            try:
                response = self._memory.add_documents_batch(
                    documents,
                    container_tag=self._container,
                    task_type="superrag",
                    dreaming="instant",
                )
            except ApiError as error:
                if error.status is None:
                    recovered_ids = self._recover_ambiguous_batch(batch)
                    if recovered_ids is None:
                        raise
                    response = {
                        "results": [{"id": value} for value in recovered_ids],
                        "success": len(recovered_ids),
                        "failed": 0,
                    }
                elif error.status == 429 and throttle_retries < self._max_throttle_retries:
                    throttles += 1
                    throttle_retries += 1
                    batch_size = max(1, batch_size // 2)
                    self._sleep(self._retry_seconds(error.retry_after))
                    continue
                elif error.status == 413 and batch_size > 1:
                    batch_size = max(1, batch_size // 2)
                    continue
                elif error.status is not None:
                    raise
            results = _items(response.get("results"))
            success = int(response.get("success") or len(results))
            failed = int(response.get("failed") or 0)
            ids = [str(item.get("id")) for item in results if item.get("id")]
            if failed or success != len(batch) or len(ids) != len(batch):
                raise RuntimeError("batch acknowledgement was partial or lacked exact IDs")
            accepted.extend(item.custom_id for item in batch)
            document_ids.extend(ids)
            accepted_set.update(item.custom_id for item in batch)
            pending = [item for item in manifest.records if item.custom_id not in accepted_set]
            batch_size = min(self._maximum_batch, batch_size + 1)
            throttle_retries = 0
            latest = self._checkpoint(
                manifest,
                accepted=accepted,
                document_ids=document_ids,
                batch_size=batch_size,
                attempts=attempts,
                throttles=throttles,
            )
            self._sink(latest)
            accepted_batches += 1
            if max_accepted_batches is not None and accepted_batches >= max_accepted_batches:
                break
        return latest

    def reconcile(self, manifest: SignedIngestionManifest) -> IngestionReport:
        if not self.verify_manifest(manifest):
            raise PermissionError("ingestion manifest signature is invalid")
        documents = self._inventory_documents()
        processing = self._memory.get_processing_documents(
            container_tags=[self._container]
        )
        processing_docs = _items(processing.get("documents"))
        processing_ids = {
            str(item.get("id")) for item in processing_docs if item.get("id")
        }
        expected = {item.custom_id: item for item in manifest.records}
        imported: List[Tuple[Mapping[str, Any], Mapping[str, Any], str]] = []
        for document in documents:
            metadata = document.get("metadata")
            metadata = metadata if isinstance(metadata, Mapping) else {}
            if metadata.get("ingestionRunId") != self._run_id:
                continue
            custom_id = str(
                document.get("customId") or metadata.get("sourceCustomId") or ""
            )
            imported.append((document, metadata, custom_id))
        grouped: Dict[str, List[Tuple[Mapping[str, Any], Mapping[str, Any]]]] = {}
        for document, metadata, custom_id in imported:
            grouped.setdefault(custom_id, []).append((document, metadata))
        missing = tuple(sorted(set(expected) - set(grouped)))
        unexpected = tuple(sorted(set(grouped) - set(expected)))
        duplicates = tuple(
            sorted(key for key, values in grouped.items() if len(values) != 1)
        )
        mismatches = tuple(
            sorted(
                key
                for key, record in expected.items()
                if key in grouped
                and any(
                    metadata.get("sourceHash") != record.source_hash
                    for _, metadata in grouped[key]
                )
            )
        )
        failed = sum(
            1
            for document, _, _ in imported
            if str(document.get("status") or "").lower() == "failed"
        )
        in_processing = sum(
            1
            for document, _, _ in imported
            if str(document.get("id") or "") in processing_ids
            or str(document.get("status") or "").lower() not in {"done", "failed"}
        )
        done = sum(
            1
            for document, _, _ in imported
            if str(document.get("status") or "").lower() == "done"
            and str(document.get("id") or "") not in processing_ids
        )
        exact = (
            len(imported) == len(expected)
            and not missing
            and not unexpected
            and not duplicates
            and not mismatches
        )
        return IngestionReport(
            self._run_id,
            len(expected),
            len(imported),
            done,
            in_processing,
            failed,
            missing,
            duplicates,
            mismatches,
            unexpected,
            exact,
            exact and done == len(expected) and in_processing == 0 and failed == 0,
        )

    def wait_until_ready(
        self,
        manifest: SignedIngestionManifest,
        *,
        timeout_seconds: float = 180.0,
        poll_seconds: float = 3.0,
    ) -> IngestionReport:
        deadline = time.monotonic() + timeout_seconds
        last: Optional[IngestionReport] = None
        while time.monotonic() < deadline:
            last = self.reconcile(manifest)
            if last.semantically_ready:
                return last
            if last.failed_count:
                raise RuntimeError("one or more ingested documents failed processing")
            time.sleep(poll_seconds)
        raise TimeoutError(
            "ingestion did not become ready; "
            f"last={asdict(last) if last is not None else None}"
        )
