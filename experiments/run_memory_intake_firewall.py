"""Live consent-, purpose-, sensitivity-, and replay-bound memory ingestion."""

from datetime import datetime, timedelta, timezone
import json
import secrets
from typing import Any, Dict, Mapping

from supermemory_lab.config import load_config
from supermemory_lab.authorization import TestingAuthorizationLedger
from supermemory_lab.intake_firewall import (
    IntakeAuthorization,
    IntakeRequest,
    MemoryIntakeFirewall,
)
from supermemory_lab.live import build_live_clients
from supermemory_lab.trace import RunTrace


def _identity() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{stamp}-{secrets.token_hex(3)}"


def _authorize(proposal, actor: str = "synthetic-subject-owner") -> IntakeAuthorization:
    return IntakeAuthorization(
        proposal.proposal_hash,
        proposal.request_hash,
        proposal.grant_hash,
        proposal.decision,
        actor,
    )


def _document_id(response: Mapping[str, Any]) -> str:
    value = response.get("id") or response.get("documentId")
    if not isinstance(value, str) or not value:
        raise RuntimeError("intake document response omitted ID")
    return value


def main() -> None:
    identity = _identity()
    suffix = identity[-6:]
    workspace = f"lab:intake-firewall:{identity}"
    other_workspace = f"lab:intake-firewall:other:{identity}"
    subject = f"synthetic-subject-{suffix}"
    purpose = "assistant-personalization"
    safe_preference = f"Synthetic preference {suffix}: use concise Markdown weekly summaries."
    safe_conversation = (
        f"Synthetic conversation {suffix}: The subject explicitly asked the assistant to "
        "remember that weekly project summaries are reviewed on Friday."
    )
    denied_secret = f"api_key=synthetic-never-store-{suffix}-0123456789"
    other_fact = f"Other tenant private preference {suffix}: expose nothing."
    now = datetime.now(timezone.utc)
    clients = build_live_clients(load_config())
    firewall = MemoryIntakeFirewall(
        clients.memory,
        clients.llm,
        container_tag=workspace,
        signing_key=secrets.token_bytes(32),
        authorization_ledger=TestingAuthorizationLedger(trust_first_use=True),
    )
    grant = firewall.issue_grant(
        grant_id=f"consent-{suffix}",
        subject=subject,
        purpose=purpose,
        categories=["preference", "conversation", "health"],
        issued_at=now - timedelta(minutes=1),
        expires_at=now + timedelta(days=30),
        max_retention_days=14,
        allow_static=False,
    )
    trace = RunTrace(
        f"intake-firewall-{identity}", experiment="consent-aware-memory-intake-firewall"
    )
    evaluation: Dict[str, Any] = {}
    cleanup: Dict[str, Any] = {}
    try:
        clients.memory.create_memories(
            other_workspace,
            [{"content": other_fact, "metadata": {"kind": "private-control"}}],
        )
        safe_request = IntakeRequest(
            f"safe-preference-{suffix}",
            subject,
            purpose,
            "preference",
            safe_preference,
            "explicit-user-setting",
            True,
            "dynamic",
            7,
        )
        conversation_request = IntakeRequest(
            f"safe-conversation-{suffix}",
            subject,
            purpose,
            "conversation",
            safe_conversation,
            "role-preserving-session",
            True,
            "document",
            7,
        )
        denied_requests = [
            IntakeRequest(
                f"secret-{suffix}",
                subject,
                purpose,
                "preference",
                denied_secret,
                "untrusted-message",
                True,
                "dynamic",
                7,
            ),
            IntakeRequest(
                f"health-{suffix}",
                subject,
                purpose,
                "health",
                "Synthetic health observation requiring special review.",
                "conversation-inference",
                True,
                "dynamic",
                7,
                "restricted",
            ),
            IntakeRequest(
                f"implicit-{suffix}",
                subject,
                purpose,
                "preference",
                "Assistant inferred a possible preference without save consent.",
                "model-inference",
                False,
                "dynamic",
                7,
            ),
            IntakeRequest(
                f"purpose-{suffix}",
                subject,
                "advertising",
                "preference",
                "Reuse assistant memory for targeted advertising.",
                "purpose-expansion",
                True,
                "dynamic",
                7,
            ),
        ]
        safe_proposal = trace.capture(
            "propose_consented_dynamic_memory",
            "openrouter+policy",
            lambda: firewall.propose(safe_request, grant, now=now),
            summarize=lambda value: {
                "decision": value.decision,
                "modelLabel": value.model_label,
                "signatureValid": firewall.verify_proposal(value),
            },
        )
        conversation_proposal = trace.capture(
            "propose_filtered_conversation_ingest",
            "openrouter+policy",
            lambda: firewall.propose(conversation_request, grant, now=now),
            summarize=lambda value: {
                "decision": value.decision,
                "modelLabel": value.model_label,
                "signatureValid": firewall.verify_proposal(value),
            },
        )
        denied_proposals = [
            trace.capture(
                f"deny_or_review_{request.request_id.split('-', 1)[0]}",
                "openrouter+policy",
                lambda request=request: firewall.propose(request, grant, now=now),
                summarize=lambda value: {
                    "decision": value.decision,
                    "reasons": value.reasons,
                    "modelLabel": value.model_label,
                    "previewRedacted": "synthetic-never-store" not in value.redacted_preview,
                },
            )
            for request in denied_requests
        ]
        denied_writes = 0
        for request, proposal in zip(denied_requests, denied_proposals):
            try:
                firewall.apply(proposal, request, grant, _authorize(proposal), now=now)
            except PermissionError:
                denied_writes += 1

        wrong_authorization_denied = False
        try:
            wrong = _authorize(safe_proposal)
            firewall.apply(
                safe_proposal,
                safe_request,
                grant,
                IntakeAuthorization(
                    "wrong-proposal",
                    wrong.request_hash,
                    wrong.grant_hash,
                    wrong.decision,
                    wrong.actor,
                ),
                now=now,
            )
        except PermissionError:
            wrong_authorization_denied = True
        dynamic_result = trace.capture(
            "store_expiring_consented_preference",
            "supermemory",
            lambda: firewall.apply(
                safe_proposal, safe_request, grant, _authorize(safe_proposal), now=now
            ),
            summarize=lambda value: {"created": len(value.get("memories") or [])},
        )
        document_result = trace.capture(
            "store_purpose_filtered_conversation",
            "supermemory",
            lambda: firewall.apply(
                conversation_proposal,
                conversation_request,
                grant,
                _authorize(conversation_proposal),
                now=now,
            ),
            summarize=lambda value: {
                "id": value.get("id") or value.get("documentId"),
                "status": value.get("status"),
            },
        )
        document_id = _document_id(document_result)
        processed = clients.memory.wait_for_document(
            document_id, timeout_seconds=120, poll_seconds=3
        )
        clients.memory.wait_for_memory(
            suffix,
            container_tag=workspace,
            search_mode="memories",
            threshold=0.0,
            required_text=safe_preference,
            timeout_seconds=60,
            poll_seconds=1,
        )
        replay_denied = False
        try:
            firewall.apply(
                safe_proposal, safe_request, grant, _authorize(safe_proposal), now=now
            )
        except RuntimeError:
            replay_denied = True

        profile = trace.capture(
            "read_consent_safe_profile",
            "supermemory",
            lambda: clients.memory.profile(
                workspace,
                query="weekly project summary preferences and schedule",
                threshold=0.0,
                include=["static", "dynamic", "buckets"],
            ),
            summarize=lambda value: {
                "staticCount": len((value.get("profile") or {}).get("static") or []),
                "dynamicCount": len((value.get("profile") or {}).get("dynamic") or []),
            },
        )
        search = clients.memory.search_memories(
            "weekly project summary preferences and schedule",
            container_tag=workspace,
            search_mode="hybrid",
            threshold=0.0,
            limit=20,
            include={"documents": True},
        )
        inventory = clients.memory.list_memory_entries([workspace], limit=50, page=1)
        documents = clients.memory.list_documents(
            container_tags=[workspace], limit=50, page=1
        )
        serialized = json.dumps(
            {"profile": profile, "search": search, "inventory": inventory},
            default=str,
        )
        raw_documents = (
            documents.get("documents")
            or documents.get("memories")
            or documents.get("results")
            or []
        )
        conversation_documents = [
            item
            for item in raw_documents
            if isinstance(item, Mapping)
            and item.get("customId") == conversation_request.request_id
        ]
        expiry_present = "forgetAfter" in json.dumps(inventory, default=str)
        decisions = [proposal.decision for proposal in denied_proposals]
        evaluation = {
            "safeDynamicDecision": safe_proposal.decision,
            "safeDocumentDecision": conversation_proposal.decision,
            "deniedDecisions": decisions,
            "allSensitiveWritesDenied": denied_writes == len(denied_requests),
            "secretPreviewRedacted": "synthetic-never-store"
            not in denied_proposals[0].redacted_preview,
            "wrongAuthorizationDenied": wrong_authorization_denied,
            "dynamicCreated": len(dynamic_result.get("memories") or []) == 1,
            "filteredDocumentDone": processed.get("status") == "done",
            "conversationDocumentPresent": len(conversation_documents) == 1,
            "expiryPresentInInventory": expiry_present,
            "safePreferencePresent": safe_preference.casefold() in serialized.casefold(),
            "deniedSecretAbsent": denied_secret.casefold() not in serialized.casefold(),
            "sensitiveHealthAbsent": "special review" not in serialized.casefold(),
            "purposeExpansionAbsent": "targeted advertising" not in serialized.casefold(),
            "otherTenantAbsent": other_fact.casefold() not in serialized.casefold(),
            "replayDenied": replay_denied,
            "auditEvents": [str(item.get("event")) for item in firewall.audit_events],
        }
        evaluation["passed"] = all(
            (
                evaluation["safeDynamicDecision"] == "STORE_DYNAMIC",
                evaluation["safeDocumentDecision"] == "STORE_DOCUMENT",
                decisions == ["DENY", "REVIEW", "REVIEW", "DENY"],
                evaluation["allSensitiveWritesDenied"],
                evaluation["secretPreviewRedacted"],
                evaluation["wrongAuthorizationDenied"],
                evaluation["dynamicCreated"],
                evaluation["filteredDocumentDone"],
                evaluation["conversationDocumentPresent"],
                evaluation["expiryPresentInInventory"],
                evaluation["safePreferencePresent"],
                evaluation["deniedSecretAbsent"],
                evaluation["sensitiveHealthAbsent"],
                evaluation["purposeExpansionAbsent"],
                evaluation["otherTenantAbsent"],
                evaluation["replayDenied"],
            )
        )
        trace.metric("evaluation", evaluation)
    finally:
        for name, container in {"subject": workspace, "other": other_workspace}.items():
            try:
                cleanup[name] = clients.memory.delete_container(container)
            except Exception as error:
                cleanup[name] = {
                    "error": type(error).__name__,
                    "detail": str(error)[:200],
                }
        trace.metric("cleanup", cleanup)

    path = trace.write()
    print(json.dumps({"trace": str(path), "evaluation": evaluation, "cleanup": cleanup}, indent=2))


if __name__ == "__main__":
    main()
