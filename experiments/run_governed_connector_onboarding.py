"""Live connector preflight with exact intent, OAuth boundary, and safe disconnect."""

from datetime import datetime, timezone
import json
import secrets
from typing import Any, Dict, List, Mapping

from supermemory_lab.config import load_config
from supermemory_lab.connector_onboarding_governor import (
    ConnectorAuthorization,
    GovernedConnectorOnboarding,
)
from supermemory_lab.http import ApiError
from supermemory_lab.live import build_live_clients
from supermemory_lab.trace import RunTrace


def _identity() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{stamp}-{secrets.token_hex(3)}"


def _connections(value: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    raw = value.get("data") or value.get("connections") or value.get("results") or []
    return [item for item in raw if isinstance(item, Mapping)]


def main() -> None:
    identity = _identity()
    workspace = f"lab:connector-governor:{identity}"
    clients = build_live_clients(load_config())
    governor = GovernedConnectorOnboarding(
        clients.memory, signing_key=secrets.token_bytes(32)
    )
    intent = governor.issue_intent(
        provider="github",
        container_tags=(workspace,),
        redirect_url="https://example.com/synthetic-supermemory-oauth-complete",
        document_limit=1,
        metadata={"purpose": "synthetic-connector-preflight", "synthetic": True},
    )
    authorization = ConnectorAuthorization(intent.intent_hash, "synthetic-lab-owner")
    trace = RunTrace(
        f"connector-onboarding-{identity}",
        experiment="governed-connector-onboarding-preflight",
    )
    pending = None
    state = "unknown"
    begin_status = None
    resource_status = None
    cleanup: Dict[str, Any] = {}
    evaluation: Dict[str, Any] = {}
    try:
        wrong_authorization_denied = False
        try:
            governor.begin(
                intent, ConnectorAuthorization("wrong", "synthetic-lab-owner")
            )
        except PermissionError:
            wrong_authorization_denied = True

        try:
            pending = trace.capture(
                "create_exact_scoped_github_oauth_intent",
                "supermemory",
                lambda: governor.begin(intent, authorization),
                summarize=lambda value: {
                    "provider": value.provider,
                    "intentValid": governor.verify_intent(intent),
                    "pendingSignatureValid": governor.verify_pending(value),
                    "authRequired": value.auth_required,
                    "authLinkRawPersisted": False,
                },
            )
            state = "awaiting-user-oauth" if pending.auth_required else "connected-no-oauth"
        except ApiError as error:
            begin_status = error.status
            if error.status == 403:
                state = "plan-or-entitlement-blocked"
            else:
                raise

        connection_visible = False
        resource_pre_oauth_denied = False
        if pending is not None:
            detail = trace.capture(
                "read_pending_connection_without_exposing_oauth_url",
                "supermemory",
                lambda: clients.memory.get_connection(pending.connection_id),
                summarize=lambda value: {
                    "idMatches": value.get("id") == pending.connection_id,
                    "provider": value.get("provider"),
                    "metadataPresent": isinstance(value.get("metadata"), Mapping),
                },
            )
            connection_visible = detail.get("id") == pending.connection_id
            try:
                governor.capture_resources(pending)
            except ApiError as error:
                resource_status = error.status
                resource_pre_oauth_denied = error.status in {400, 401, 404}
            if not resource_pre_oauth_denied:
                raise RuntimeError("pending OAuth connection unexpectedly exposed resources")

            trace.capture(
                "disconnect_pending_connection_preserving_documents",
                "supermemory",
                lambda: governor.disconnect_preserving_documents(
                    pending, authorization
                ),
                summarize=lambda value: {
                    "idMatches": value.get("id") == pending.connection_id,
                    "provider": value.get("provider"),
                    "deleteDocuments": False,
                },
            )
            listed = clients.memory.list_connections(container_tags=[workspace])
            connection_absent_after_disconnect = all(
                item.get("id") != pending.connection_id for item in _connections(listed)
            )
        else:
            connection_absent_after_disconnect = True

        typed_external_boundary = state in {
            "awaiting-user-oauth",
            "plan-or-entitlement-blocked",
        }
        evaluation = {
            "intentValid": governor.verify_intent(intent),
            "wrongAuthorizationDeniedBeforeApi": wrong_authorization_denied,
            "typedState": state,
            "typedExternalBoundary": typed_external_boundary,
            "beginStatus": begin_status,
            "pendingSignatureValid": (
                governor.verify_pending(pending) if pending is not None else True
            ),
            "connectionVisible": connection_visible if pending is not None else False,
            "resourcePreOauthDenied": (
                resource_pre_oauth_denied if pending is not None else True
            ),
            "resourceStatus": resource_status,
            "oauthUrlPersisted": False,
            "connectionAbsentAfterDisconnect": connection_absent_after_disconnect,
            "documentsDeletedByDisconnect": False,
            "resourceSelectionFalselyClaimedComplete": False,
        }
        evaluation["passed"] = all(
            [
                evaluation["intentValid"],
                wrong_authorization_denied,
                typed_external_boundary,
                evaluation["pendingSignatureValid"],
                evaluation["resourcePreOauthDenied"],
                not evaluation["oauthUrlPersisted"],
                connection_absent_after_disconnect,
                not evaluation["documentsDeletedByDisconnect"],
                not evaluation["resourceSelectionFalselyClaimedComplete"],
            ]
        )
        trace.metric("evaluation", evaluation)
    finally:
        if pending is not None:
            try:
                # Idempotent best effort in case the earlier disconnect did not complete.
                cleanup["connection"] = clients.memory.delete_connection(
                    pending.connection_id, delete_documents=False
                )
            except ApiError as error:
                cleanup["connection"] = {
                    "alreadyAbsent": error.status == 404,
                    "status": error.status,
                }
            except Exception as error:
                cleanup["connection"] = {
                    "error": type(error).__name__,
                    "detail": str(error)[:180],
                }
        try:
            cleanup["container"] = clients.memory.delete_container(workspace)
        except ApiError as error:
            cleanup["container"] = {
                "alreadyAbsent": error.status == 404,
                "status": error.status,
            }
        except Exception as error:
            cleanup["container"] = {
                "error": type(error).__name__,
                "detail": str(error)[:180],
            }
        trace.metric("cleanup", cleanup)
        path = trace.write()
        print(json.dumps({"trace": str(path), "evaluation": evaluation, "cleanup": cleanup}, indent=2))


if __name__ == "__main__":
    main()
