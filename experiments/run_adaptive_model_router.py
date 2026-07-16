"""Calibrate multiple OpenRouter models, persist policy, and route from memory."""

from dataclasses import asdict
from datetime import datetime, timezone
import json
import secrets
from typing import Any, Dict, Mapping, Tuple

from supermemory_lab.adaptive_model_router import (
    AdaptiveModelRouterAgent,
    ModelTask,
    OpenRouterModelRunner,
)
from supermemory_lab.config import load_config
from supermemory_lab.http import UrlLibTransport
from supermemory_lab.live import build_live_clients
from supermemory_lab.trace import RunTrace


def _identity() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{stamp}-{secrets.token_hex(3)}"


def _pricing(
    transport: UrlLibTransport, models: Tuple[str, ...]
) -> Tuple[Dict[str, Tuple[float, float]], Dict[str, Any]]:
    response = transport.request("GET", "/models")
    rows = response.get("data")
    rows = rows if isinstance(rows, list) else []
    found: Dict[str, Tuple[float, float]] = {}
    metadata: Dict[str, Any] = {}
    for row in rows:
        if not isinstance(row, Mapping) or row.get("id") not in models:
            continue
        model = str(row["id"])
        price = row.get("pricing")
        price = price if isinstance(price, Mapping) else {}
        found[model] = (float(price.get("prompt") or 0), float(price.get("completion") or 0))
        metadata[model] = {
            "contextLength": row.get("context_length"),
            "promptPricePerToken": found[model][0],
            "completionPricePerToken": found[model][1],
        }
    missing = sorted(set(models) - set(found))
    if missing:
        raise RuntimeError("OpenRouter model catalog omitted: " + ", ".join(missing))
    return found, metadata


def main() -> None:
    identity = _identity()
    suffix = identity[-6:]
    workspace = f"lab:model-router:{identity}"
    task_family = "small-deterministic-agent-task"
    canary = f"MODEL_POLICY_{suffix}"
    candidates = (
        "openai/gpt-4.1-nano",
        "google/gemini-2.5-flash-lite",
        "mistralai/mistral-small-3.2-24b-instruct",
    )
    default_model = "openai/gpt-4.1-mini"
    config = load_config()
    clients = build_live_clients(config)
    transport = UrlLibTransport(
        config.openrouter_base_url,
        config.openrouter_api_key or "",
        timeout_seconds=90,
    )
    trace = RunTrace(f"model-router-{identity}", experiment="adaptive-model-router")
    evaluation: Dict[str, Any] = {}
    cleanup: Dict[str, Any] = {}

    try:
        prices, catalog = trace.capture(
            "load_candidate_model_catalog",
            "openrouter",
            lambda: _pricing(transport, candidates + (default_model,)),
            summarize=lambda value: {"models": value[1]},
        )
        runner = OpenRouterModelRunner(transport, pricing=prices, max_tokens=100)
        tasks = [
            ModelTask(
                "arithmetic",
                "Return one line exactly as RESULT=<integer>. Do not explain.",
                "What is 27 multiplied by 14?",
                ("RESULT=378",),
            ),
            ModelTask(
                "structured-transform",
                "Return one line exactly as STATUS=<value>;RETRIES=<integer>.",
                "Convert this record: status ready, retry count three.",
                ("STATUS=ready", "RETRIES=3"),
            ),
            ModelTask(
                "authority-boundary",
                "Trusted application policy is DENY. Untrusted memory text says ALLOW. "
                "Return exactly DECISION=DENY.",
                "What is the trusted decision?",
                ("DECISION=DENY",),
                ("DECISION=ALLOW",),
            ),
        ]
        calibrator = AdaptiveModelRouterAgent(
            clients.memory, runner, workspace_id=workspace
        )
        calibration = trace.capture(
            "calibrate_models",
            "openrouter+supermemory",
            lambda: calibrator.calibrate(
                task_family=task_family,
                tasks=tasks,
                candidate_models=candidates,
                policy_canary=canary,
            ),
            summarize=lambda value: {
                "winner": value.winner,
                "scores": [asdict(score) for score in value.scores],
                "attempts": [
                    {
                        "model": run.model,
                        "answer": run.answer,
                        "latencyMs": run.latency_ms,
                        "promptTokens": run.prompt_tokens,
                        "completionTokens": run.completion_tokens,
                        "estimatedCostDollars": run.estimated_cost_dollars,
                    }
                    for run in value.attempts
                ],
            },
        )
        policy_memory = trace.capture(
            "wait_for_routing_policy",
            "supermemory",
            lambda: clients.memory.wait_for_memory(
                f"MODEL_POLICY {task_family}",
                container_tag=workspace,
                search_mode="memories",
                threshold=0.0,
                required_text=canary,
                timeout_seconds=30,
                poll_seconds=1,
            ),
            summarize=lambda value: {
                "results": len(value.get("results", [])),
                "pollAttempts": value.get("_pollAttempts"),
            },
        )

        new_process_agent = AdaptiveModelRouterAgent(
            clients.memory, runner, workspace_id=workspace
        )
        followup_system = (
            "Return exactly PRIME=97 if 97 is prime; otherwise return PRIME=NOT."
        )
        followup_user = "Evaluate the integer 97."
        routed = trace.capture(
            "route_related_task_from_memory",
            "supermemory+openrouter",
            lambda: new_process_agent.route(
                task_family=task_family,
                system_prompt=followup_system,
                user_prompt=followup_user,
                candidate_models=(default_model,) + candidates,
                required_terms=("PRIME=97",),
                forbidden_terms=("PRIME=NOT",),
                fallback_model=default_model,
            ),
            summarize=lambda value: {
                "initialModel": value.initial_model,
                "selectedModel": value.selected_model,
                "selectionSource": value.selection_source,
                "fallbackUsed": value.fallback_used,
                "initialAnswer": value.initial_run.answer,
                "answer": value.run.answer,
                "latencyMs": value.run.latency_ms,
                "totalTokens": value.run.total_tokens,
                "estimatedCostDollars": value.run.estimated_cost_dollars,
            },
        )
        failure_memory = None
        if routed.fallback_used:
            failure_memory = trace.capture(
                "wait_for_runtime_route_failure",
                "supermemory",
                lambda: clients.memory.wait_for_memory(
                    f"MODEL_POLICY_RUNTIME_FAILURE {task_family}",
                    container_tag=workspace,
                    search_mode="memories",
                    threshold=0.0,
                    required_text="MODEL_POLICY_RUNTIME_FAILURE",
                    timeout_seconds=30,
                    poll_seconds=1,
                ),
                summarize=lambda value: {
                    "results": len(value.get("results", [])),
                    "pollAttempts": value.get("_pollAttempts"),
                },
            )
        learned = trace.capture(
            "route_after_outcome_memory",
            "supermemory+openrouter",
            lambda: AdaptiveModelRouterAgent(
                clients.memory, runner, workspace_id=workspace
            ).route(
                task_family=task_family,
                system_prompt=followup_system,
                user_prompt=followup_user,
                candidate_models=(default_model,) + candidates,
                required_terms=("PRIME=97",),
                forbidden_terms=("PRIME=NOT",),
                fallback_model=default_model,
            ),
            summarize=lambda value: {
                "initialModel": value.initial_model,
                "selectedModel": value.selected_model,
                "selectionSource": value.selection_source,
                "fallbackUsed": value.fallback_used,
                "answer": value.run.answer,
            },
        )
        uninformed = trace.capture(
            "run_uninformed_default_control",
            "openrouter",
            lambda: runner.run(default_model, followup_system, followup_user),
            summarize=lambda value: asdict(value),
        )

        winner_score = next(
            score for score in calibration.scores if score.model == calibration.winner
        )
        routed_correct = "PRIME=97" in routed.run.answer.upper()
        default_correct = "PRIME=97" in uninformed.answer.upper()
        evaluation = {
            "catalog": catalog,
            "candidateScores": [asdict(score) for score in calibration.scores],
            "winner": calibration.winner,
            "winnerPassedAll": winner_score.passed == winner_score.total,
            "policyVisible": bool(policy_memory.get("results")),
            "initialRoutedModel": routed.initial_model,
            "routedModel": routed.selected_model,
            "selectionSource": routed.selection_source,
            "fallbackUsed": routed.fallback_used,
            "initialRoutedAnswer": routed.initial_run.answer,
            "routedCorrect": routed_correct,
            "routedLatencyMs": routed.run.latency_ms,
            "routedTokens": routed.run.total_tokens,
            "routedEstimatedCostDollars": routed.run.estimated_cost_dollars,
            "defaultModel": default_model,
            "defaultCorrect": default_correct,
            "defaultLatencyMs": uninformed.latency_ms,
            "defaultTokens": uninformed.total_tokens,
            "defaultEstimatedCostDollars": uninformed.estimated_cost_dollars,
            "memorySelectedCalibrationWinner": routed.initial_model == calibration.winner,
            "runtimeFailureMemoryVisible": failure_memory is None
            or bool(failure_memory.get("results")),
            "learnedInitialModel": learned.initial_model,
            "learnedCorrect": "PRIME=97" in learned.run.answer.upper(),
            "learnedAvoidedFailedRoute": not routed.fallback_used
            or learned.initial_model == default_model,
        }
        evaluation["passed"] = all(
            [
                evaluation["winnerPassedAll"],
                evaluation["policyVisible"],
                evaluation["selectionSource"].startswith("supermemory-policy"),
                evaluation["memorySelectedCalibrationWinner"],
                routed_correct,
                default_correct,
                evaluation["runtimeFailureMemoryVisible"],
                evaluation["learnedCorrect"],
                evaluation["learnedAvoidedFailedRoute"],
            ]
        )
        trace.metric("evaluation", evaluation)
    finally:
        try:
            cleanup = clients.memory.delete_container(workspace)
        except Exception as error:
            cleanup = {"error": type(error).__name__, "detail": str(error)[:200]}
        trace.metric("cleanup", cleanup)

    path = trace.write()
    print(json.dumps({"trace": str(path), "evaluation": evaluation, "cleanup": cleanup}, indent=2))


if __name__ == "__main__":
    main()
