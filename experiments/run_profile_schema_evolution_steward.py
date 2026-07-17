"""Live AI-suggested profile schema evolution with drift and replay controls."""

from dataclasses import asdict
from datetime import datetime, timezone
import json
import secrets
import time
from typing import Any, Dict, Mapping

from supermemory_lab.config import load_config
from supermemory_lab.authorization import TestingAuthorizationLedger
from supermemory_lab.live import build_live_clients
from supermemory_lab.profile_schema_steward import (
    BucketEvolutionAuthorization,
    GovernedProfileSchemaSteward,
)
from supermemory_lab.trace import RunTrace


from supermemory_lab.integrity import new_run_identity


_identity = new_run_identity


def _wait_for_bucket_memory(memory, container: str, bucket: str, marker: str) -> Dict[str, Any]:
    deadline = time.monotonic() + 90
    attempts = 0
    last: Dict[str, Any] = {}
    while time.monotonic() < deadline:
        attempts += 1
        last = memory.profile(
            container,
            query=marker,
            threshold=0.0,
            include=["static", "dynamic", "buckets"],
            buckets=[bucket],
        )
        if marker in json.dumps(last, ensure_ascii=False, default=str):
            last["_pollAttempts"] = attempts
            return last
        time.sleep(2)
    raise TimeoutError(f"profile bucket memory was not visible after {attempts} attempts")


def main() -> None:
    identity = _identity()
    suffix = identity[-6:].lower()
    workspace = f"lab:profile-schema:{identity}"
    other_workspace = f"lab:profile-schema:other:{identity}"
    initial_key = f"operating-constraints-{suffix}"
    concurrent_key = f"concurrent-controls-{suffix}"
    required_key = f"escalation-contracts-{suffix}"
    marker = f"ESCALATION_SCHEMA_{suffix.upper()}"
    other_marker = f"OTHER_PROFILE_{suffix.upper()}"
    clients = build_live_clients(load_config())
    steward = GovernedProfileSchemaSteward(
        clients.memory,
        container_tag=workspace,
        signing_key=secrets.token_bytes(32),
        authorization_ledger=TestingAuthorizationLedger(trust_first_use=True),
    )
    trace = RunTrace(
        f"profile-schema-{identity}",
        experiment="governed-profile-schema-evolution-steward",
    )
    cleanup: Dict[str, Any] = {}
    evaluation: Dict[str, Any] = {}
    try:
        clients.memory.create_memories(
            workspace,
            [
                {
                    "content": f"Synthetic profile schema workspace {suffix} initialized.",
                    "isStatic": True,
                    "metadata": {"kind": "workspace-seed"},
                }
            ],
        )
        clients.memory.create_memories(
            other_workspace,
            [
                {
                    "content": f"Other tenant private profile marker {other_marker}.",
                    "metadata": {"kind": "private-control"},
                }
            ],
        )
        trace.capture(
            "configure_initial_owned_bucket",
            "supermemory",
            lambda: clients.memory.update_container_settings(
                workspace,
                name="Synthetic governed profile schema",
                entity_context=(
                    "This synthetic account stores only explicit operating constraints and "
                    "escalation contracts. Do not infer sensitive traits."
                ),
                profile_buckets=[
                    {
                        "key": initial_key,
                        "description": "Explicit stable operating constraints only.",
                    }
                ],
            ),
            summarize=lambda value: {
                "containerTag": value.get("containerTag"),
                "ownBucketCount": len(value.get("profileBuckets") or []),
            },
        )
        initial = trace.capture(
            "capture_initial_effective_schema",
            "supermemory+policy",
            steward.capture,
            summarize=lambda value: {
                "ownBucketCount": len(value.own_buckets),
                "effectiveBucketCount": len(value.effective_keys),
                "signatureValid": steward.verify_snapshot(value),
            },
        )
        raw_suggestions = trace.capture(
            "request_ai_profile_bucket_suggestions",
            "supermemory",
            clients.memory.suggest_profile_buckets,
            summarize=lambda value: {
                "suggestionCount": len(value.get("suggestions") or []),
                "rawSuggestionTextPersisted": False,
            },
        )
        suggestions = steward.validate_suggestions(raw_suggestions)
        available = [item for item in suggestions if item.key not in initial.effective_keys]
        additions = [
            {
                "key": required_key,
                "description": (
                    "Explicit escalation path, owner, severity threshold, and response target."
                ),
            }
        ]
        suggestion_adopted = bool(available)
        if available:
            additions.append(asdict(available[0]))
        first_plan = trace.capture(
            "propose_additive_schema_plan",
            "policy",
            lambda: steward.propose(initial, additions),
            summarize=lambda value: {
                "additionCount": len(value.additions),
                "existingPreserved": all(
                    item in value.resulting_own_buckets for item in initial.own_buckets
                ),
                "signatureValid": steward.verify_plan(value),
            },
        )

        trace.capture(
            "simulate_concurrent_schema_change",
            "supermemory",
            lambda: clients.memory.update_container_settings(
                workspace,
                profile_buckets=[
                    *(asdict(item) for item in initial.own_buckets),
                    {
                        "key": concurrent_key,
                        "description": "Concurrent externally approved control bucket.",
                    },
                ],
            ),
            summarize=lambda value: {
                "ownBucketCount": len(value.get("profileBuckets") or [])
            },
        )
        drift_denied = False
        try:
            steward.apply(
                initial,
                first_plan,
                BucketEvolutionAuthorization(
                    initial.snapshot_hash, first_plan.plan_hash, "schema-owner"
                ),
            )
        except RuntimeError:
            drift_denied = True

        refreshed = trace.capture(
            "recapture_after_schema_drift",
            "supermemory+policy",
            steward.capture,
            summarize=lambda value: {
                "ownBucketCount": len(value.own_buckets),
                "concurrentBucketPresent": concurrent_key in value.effective_keys,
                "signatureValid": steward.verify_snapshot(value),
            },
        )
        plan = steward.propose(refreshed, additions)
        wrong_authorization_denied = False
        try:
            steward.apply(
                refreshed,
                plan,
                BucketEvolutionAuthorization("wrong", plan.plan_hash, "schema-owner"),
            )
        except PermissionError:
            wrong_authorization_denied = True
        trace.capture(
            "apply_exact_refreshed_schema_plan",
            "supermemory",
            lambda: steward.apply(
                refreshed,
                plan,
                BucketEvolutionAuthorization(
                    refreshed.snapshot_hash, plan.plan_hash, "synthetic-schema-owner"
                ),
            ),
            summarize=lambda value: {
                "ownBucketCount": len(value.get("profileBuckets") or []),
                "rawDescriptionsPersistedInTrace": False,
            },
        )
        replay_denied = False
        try:
            steward.apply(
                refreshed,
                plan,
                BucketEvolutionAuthorization(
                    refreshed.snapshot_hash, plan.plan_hash, "synthetic-schema-owner"
                ),
            )
        except RuntimeError:
            replay_denied = True
        final_schema = steward.capture()
        expected_own = {
            *(item.key for item in refreshed.own_buckets),
            *(item.key for item in plan.additions),
        }
        actual_own = {item.key for item in final_schema.own_buckets}

        clients.memory.create_memories(
            workspace,
            [
                {
                    "content": (
                        f"Explicit escalation contract {marker}: severity one pages the "
                        "synthetic incident owner within five minutes."
                    ),
                    "isStatic": True,
                    "metadata": {
                        "kind": "explicit-escalation-contract",
                        "profileBucket": required_key,
                    },
                }
            ],
        )
        bucket_profile = trace.capture(
            "verify_new_bucket_profile_memory",
            "supermemory",
            lambda: _wait_for_bucket_memory(
                clients.memory, workspace, required_key, marker
            ),
            summarize=lambda value: {
                "markerPresent": marker in json.dumps(value, default=str),
                "otherTenantPresent": other_marker in json.dumps(value, default=str),
                "pollAttempts": value.get("_pollAttempts"),
            },
        )
        profile_text = json.dumps(bucket_profile, default=str)
        evaluation = {
            "initialSnapshotValid": steward.verify_snapshot(initial),
            "suggestionCount": len(suggestions),
            "suggestionsSchemaValid": 1 <= len(suggestions) <= 6,
            "suggestionAdopted": suggestion_adopted,
            "firstPlanValid": steward.verify_plan(first_plan),
            "driftDenied": drift_denied,
            "concurrentBucketPreserved": concurrent_key in actual_own,
            "initialBucketPreserved": initial_key in actual_own,
            "requiredBucketAdded": required_key in actual_own,
            "exactOwnSchema": actual_own == expected_own,
            "wrongAuthorizationDenied": wrong_authorization_denied,
            "replayDenied": replay_denied,
            "profileMarkerVisible": marker in profile_text,
            "otherTenantAbsent": other_marker not in profile_text,
            "actionAuthorized": False,
        }
        evaluation["passed"] = all(
            [
                evaluation["initialSnapshotValid"],
                evaluation["suggestionsSchemaValid"],
                suggestion_adopted,
                evaluation["firstPlanValid"],
                drift_denied,
                evaluation["concurrentBucketPreserved"],
                evaluation["initialBucketPreserved"],
                evaluation["requiredBucketAdded"],
                evaluation["exactOwnSchema"],
                wrong_authorization_denied,
                replay_denied,
                evaluation["profileMarkerVisible"],
                evaluation["otherTenantAbsent"],
            ]
        )
        trace.metric("evaluation", evaluation)
    finally:
        for name, container in (("profile", workspace), ("other", other_workspace)):
            try:
                cleanup[name] = clients.memory.delete_container(container)
            except Exception as error:
                cleanup[name] = {
                    "error": type(error).__name__,
                    "detail": str(error)[:180],
                }
        trace.metric("cleanup", cleanup)
        path = trace.write()
        print(path)
        print(evaluation)


if __name__ == "__main__":
    main()
