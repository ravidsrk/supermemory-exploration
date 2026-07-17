"""Live Memory Router matrix for shared-pool and conversation continuity claims."""

from datetime import datetime, timezone
import json
import secrets
import time
from typing import Any, Dict, List, Mapping

from supermemory_lab.config import load_config
from supermemory_lab.evaluation import contains_text
from supermemory_lab.live import build_live_clients
from supermemory_lab.router import MemoryRouterClient
from supermemory_lab.trace import RunTrace


from supermemory_lab.integrity import new_run_identity


_identity = new_run_identity


def _summary(response: Mapping[str, Any]) -> Dict[str, Any]:
    usage = response.get("usage")
    return {
        "text": response.get("text"),
        "diagnostics": response.get("diagnostics"),
        "promptTokens": usage.get("prompt_tokens")
        if isinstance(usage, Mapping)
        else None,
        "completionTokens": usage.get("completion_tokens")
        if isinstance(usage, Mapping)
        else None,
        "model": response.get("model"),
        "finishReason": response.get("finishReason"),
    }


def _has(response: Mapping[str, Any], token: str) -> bool:
    return token.casefold() in str(response.get("text", "")).casefold()


def main() -> None:
    identity = _identity()
    suffix = identity[-6:]
    user_id = f"lab-router-user-{identity}"
    other_user_id = f"lab-router-other-{identity}"
    conversation_id = f"lab-router-conversation-{identity}"
    api_token = f"API_POOL_{suffix}"
    router_token = f"ROUTER_SESSION_{suffix}"
    replica_tokens = [
        router_token,
        f"ROUTER_REPLICA_TWO_{suffix}",
        f"ROUTER_REPLICA_THREE_{suffix}",
    ]
    config = load_config()
    if not config.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY or OPEN_ROUTER_KEY is required")
    clients = build_live_clients(config)
    router = MemoryRouterClient(
        supermemory_api_key=config.supermemory_api_key,
        provider_api_key=config.openrouter_api_key,
        provider_base_url=config.openrouter_base_url,
        model=config.openrouter_model,
        timeout_seconds=120,
    )
    trace = RunTrace(f"router-{identity}", experiment="router-continuity-matrix")
    evaluation: Dict[str, Any] = {}
    cleanup: Dict[str, Any] = {}

    try:
        clients.memory.create_memories(
            user_id,
            [
                {
                    "content": (
                        f"The user's exact synthetic API pool token is {api_token}. "
                        "Return it verbatim when asked."
                    ),
                    "isStatic": True,
                    "metadata": {"kind": "router-api-preload"},
                }
            ],
        )
        clients.memory.wait_for_memory(
            api_token,
            container_tag=user_id,
            search_mode="memories",
            threshold=0.0,
            required_text=api_token,
            timeout_seconds=30,
            poll_seconds=1,
        )

        api_with_conversation = trace.capture(
            "api_pool_with_conversation_header",
            "supermemory-router+openrouter",
            lambda: router.complete(
                user_id=user_id,
                conversation_id=f"api-header-{conversation_id}",
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Return only my exact synthetic API pool token. If unavailable, "
                            "return UNKNOWN."
                        ),
                    }
                ],
            ),
            summarize=_summary,
        )
        api_without_conversation = trace.capture(
            "api_pool_without_conversation_header",
            "supermemory-router+openrouter",
            lambda: router.complete(
                user_id=user_id,
                conversation_id=None,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Return only my exact synthetic API pool token. If unavailable, "
                            "return UNKNOWN."
                        ),
                    }
                ],
            ),
            summarize=_summary,
        )
        other_user = trace.capture(
            "other_user_negative_control",
            "supermemory-router+openrouter",
            lambda: router.complete(
                user_id=other_user_id,
                conversation_id=f"other-{conversation_id}",
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Return the exact synthetic API pool token if known; otherwise "
                            "return UNKNOWN."
                        ),
                    }
                ],
            ),
            summarize=_summary,
        )

        sessions: List[Dict[str, Any]] = []
        for index, token in enumerate(replica_tokens, start=1):
            session_id = (
                conversation_id if index == 1 else f"{conversation_id}-replica-{index}"
            )
            messages = [
                {
                    "role": "user",
                    "content": (
                        "Remember that the exact synthetic Router session token is "
                        f"{token}. Reply only ACK."
                    ),
                }
            ]
            initial_response = trace.capture(
                f"router_session_initial_{index}",
                "supermemory-router+openrouter",
                lambda session_id=session_id, messages=messages: router.complete(
                    user_id=user_id,
                    conversation_id=session_id,
                    messages=messages,
                ),
                summarize=_summary,
            )
            sessions.append(
                {
                    "id": session_id,
                    "token": token,
                    "messages": messages,
                    "initial": initial_response,
                }
            )
        time.sleep(20)
        delta_results: List[Mapping[str, Any]] = []
        for index, session in enumerate(sessions, start=1):
            delta_response = trace.capture(
                f"router_session_delta_only_{index}",
                "supermemory-router+openrouter",
                lambda session=session: router.complete(
                    user_id=user_id,
                    conversation_id=str(session["id"]),
                    messages=[
                        {
                            "role": "user",
                            "content": (
                                "Return only the exact synthetic Router session token. If "
                                "unavailable, return UNKNOWN."
                            ),
                        }
                    ],
                ),
                summarize=_summary,
            )
            delta_results.append(delta_response)
        delta = delta_results[0]
        initial_messages = sessions[0]["messages"]
        initial = sessions[0]["initial"]
        full_history = trace.capture(
            "router_session_full_history",
            "supermemory-router+openrouter",
            lambda: router.complete(
                user_id=user_id,
                conversation_id=conversation_id,
                messages=initial_messages
                + [
                    {"role": "assistant", "content": str(initial.get("text", "ACK"))},
                    {
                        "role": "user",
                        "content": (
                            "Return only the exact synthetic Router session token. If "
                            "unavailable, return UNKNOWN."
                        ),
                    },
                ],
            ),
            summarize=_summary,
        )
        new_conversation = trace.capture(
            "router_session_new_conversation",
            "supermemory-router+openrouter",
            lambda: router.complete(
                user_id=user_id,
                conversation_id=f"new-{conversation_id}",
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Return only the exact synthetic Router session token. If "
                            "unavailable, return UNKNOWN."
                        ),
                    }
                ],
            ),
            summarize=_summary,
        )
        api_visibility = clients.memory.search_memories(
            router_token,
            container_tag=user_id,
            search_mode="hybrid",
            threshold=0.0,
            limit=20,
        )

        evaluation = {
            "apiPoolWithConversation": _has(api_with_conversation, api_token),
            "apiPoolWithoutConversation": _has(api_without_conversation, api_token),
            "otherUserDoesNotLeak": not _has(other_user, api_token),
            "deltaOnlyContinuity": _has(delta, router_token),
            "deltaReplicaResults": [
                {
                    "token": token,
                    "recalled": _has(response, token),
                    "text": response.get("text"),
                }
                for token, response in zip(replica_tokens, delta_results)
            ],
            "fullHistoryContinuity": _has(full_history, router_token),
            "newConversationContinuity": _has(new_conversation, router_token),
            "newConversationReturnedApiPoolInstead": _has(
                new_conversation, api_token
            ),
            "routerWriteVisibleViaApi": contains_text(api_visibility, router_token),
            "diagnostics": {
                "apiWithConversation": api_with_conversation.get("diagnostics"),
                "apiWithoutConversation": api_without_conversation.get("diagnostics"),
                "delta": delta.get("diagnostics"),
                "fullHistory": full_history.get("diagnostics"),
                "newConversation": new_conversation.get("diagnostics"),
            },
        }
        evaluation["isolationPassed"] = evaluation["otherUserDoesNotLeak"]
        evaluation["fullHistoryControlPassed"] = evaluation["fullHistoryContinuity"]
        evaluation["deltaReplicasPassed"] = sum(
            int(result["recalled"])
            for result in evaluation["deltaReplicaResults"]
        )
        evaluation["documentedDeltaClaimObserved"] = (
            evaluation["deltaReplicasPassed"] == len(replica_tokens)
        )
        evaluation["documentedSharedPoolClaimObserved"] = any(
            [
                evaluation["apiPoolWithConversation"],
                evaluation["apiPoolWithoutConversation"],
            ]
        )
        evaluation["routerGeneratedCrossSessionClaimObserved"] = evaluation[
            "newConversationContinuity"
        ]
        evaluation["passed"] = all(
            [
                evaluation["apiPoolWithConversation"],
                evaluation["apiPoolWithoutConversation"],
                evaluation["isolationPassed"],
                evaluation["documentedDeltaClaimObserved"],
                evaluation["fullHistoryControlPassed"],
                evaluation["routerWriteVisibleViaApi"],
            ]
        )
        trace.metric("evaluation", evaluation)
    finally:
        for tag in (user_id, other_user_id):
            try:
                cleanup[tag] = clients.memory.delete_container(tag)
            except Exception as error:
                cleanup[tag] = {
                    "notFoundOrFailed": True,
                    "type": type(error).__name__,
                    "detail": str(error)[:220],
                }
        trace.metric("cleanup", cleanup)

    path = trace.write()
    print(
        json.dumps(
            {"trace": str(path), "evaluation": evaluation, "cleanup": cleanup},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
