"""Memory-guided model selection from measured quality, latency, and cost."""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import re
import statistics
import time
from typing import Any, Dict, List, Mapping, Optional, Protocol, Sequence, Tuple

from .agents import MemoryBackend
from .http import JsonTransport


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _terms_pass(text: str, required: Sequence[str], forbidden: Sequence[str]) -> bool:
    folded = text.casefold()
    return all(term.casefold() in folded for term in required) and all(
        term.casefold() not in folded for term in forbidden
    )


@dataclass(frozen=True)
class ModelTask:
    name: str
    system_prompt: str
    user_prompt: str
    required_terms: Tuple[str, ...]
    forbidden_terms: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ModelRun:
    model: str
    answer: str
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_dollars: float


@dataclass(frozen=True)
class ModelCandidateScore:
    model: str
    passed: int
    total: int
    latency_p50_ms: float
    total_cost_dollars: float
    total_tokens: int


@dataclass(frozen=True)
class ModelCalibrationReport:
    task_family: str
    winner: str
    scores: Tuple[ModelCandidateScore, ...]
    attempts: Tuple[ModelRun, ...]
    policy_canary: str


@dataclass(frozen=True)
class ModelRoutingReport:
    task_family: str
    initial_model: str
    selected_model: str
    selection_source: str
    memory_visible: bool
    fallback_used: bool
    initial_run: ModelRun
    run: ModelRun


class ModelRunner(Protocol):
    def run(self, model: str, system_prompt: str, user_prompt: str) -> ModelRun:
        ...


class OpenRouterModelRunner:
    """Executes a pinned OpenRouter model and records comparable usage metrics."""

    def __init__(
        self,
        transport: JsonTransport,
        *,
        pricing: Optional[Mapping[str, Tuple[float, float]]] = None,
        max_tokens: int = 220,
    ) -> None:
        self._transport = transport
        self._pricing = dict(pricing or {})
        self._max_tokens = max_tokens

    def run(self, model: str, system_prompt: str, user_prompt: str) -> ModelRun:
        started = time.perf_counter()
        response = self._transport.request(
            "POST",
            "/chat/completions",
            {
                "model": model,
                "temperature": 0,
                "max_tokens": self._max_tokens,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
        )
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], Mapping):
            raise RuntimeError(f"model {model} response omitted choices")
        message = choices[0].get("message")
        if not isinstance(message, Mapping) or not isinstance(message.get("content"), str):
            raise RuntimeError(f"model {model} response omitted text")
        usage = response.get("usage")
        usage = usage if isinstance(usage, Mapping) else {}
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        total_tokens = int(usage.get("total_tokens") or prompt_tokens + completion_tokens)
        reported_cost = usage.get("cost")
        if isinstance(reported_cost, (int, float)):
            cost = float(reported_cost)
        else:
            input_price, output_price = self._pricing.get(model, (0.0, 0.0))
            cost = prompt_tokens * input_price + completion_tokens * output_price
        return ModelRun(
            model=model,
            answer=message["content"].strip(),
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_dollars=round(cost, 9),
        )


class AdaptiveModelRouterAgent:
    """Learns a task-family routing policy and recalls it in a later process."""

    def __init__(self, memory: MemoryBackend, runner: ModelRunner, *, workspace_id: str) -> None:
        self._memory = memory
        self._runner = runner
        self._workspace_id = workspace_id

    def calibrate(
        self,
        *,
        task_family: str,
        tasks: Sequence[ModelTask],
        candidate_models: Sequence[str],
        policy_canary: str,
    ) -> ModelCalibrationReport:
        if not tasks or not candidate_models:
            raise ValueError("calibration requires tasks and candidate models")
        attempts: List[ModelRun] = []
        scores: List[ModelCandidateScore] = []
        for model in candidate_models:
            model_runs: List[ModelRun] = []
            passed = 0
            for task in tasks:
                run = self._runner.run(model, task.system_prompt, task.user_prompt)
                attempts.append(run)
                model_runs.append(run)
                passed += int(
                    _terms_pass(run.answer, task.required_terms, task.forbidden_terms)
                )
            scores.append(
                ModelCandidateScore(
                    model=model,
                    passed=passed,
                    total=len(tasks),
                    latency_p50_ms=round(
                        statistics.median(run.latency_ms for run in model_runs), 1
                    ),
                    total_cost_dollars=round(
                        sum(run.estimated_cost_dollars for run in model_runs), 9
                    ),
                    total_tokens=sum(run.total_tokens for run in model_runs),
                )
            )
        winner = sorted(
            scores,
            key=lambda score: (
                -score.passed,
                score.total_cost_dollars,
                score.latency_p50_ms,
                score.model,
            ),
        )[0]
        observed_at = _now()
        self._memory.create_memories(
            self._workspace_id,
            [
                {
                    "content": (
                        f"{policy_canary} MODEL_POLICY task_family={task_family} "
                        f"selected_model={winner.model} quality={winner.passed}/{winner.total} "
                        f"calibration_cost_usd={winner.total_cost_dollars:.9f} "
                        f"latency_p50_ms={winner.latency_p50_ms:.1f} observed_at={observed_at}. "
                        "Recalibrate after model, prompt, price, or workload changes."
                    ),
                    "isStatic": False,
                    "metadata": {
                        "kind": "model-routing-policy",
                        "taskFamily": task_family,
                        "selectedModel": winner.model,
                        "observedAt": observed_at,
                    },
                }
            ],
        )
        return ModelCalibrationReport(
            task_family=task_family,
            winner=winner.model,
            scores=tuple(scores),
            attempts=tuple(attempts),
            policy_canary=policy_canary,
        )

    def route(
        self,
        *,
        task_family: str,
        system_prompt: str,
        user_prompt: str,
        candidate_models: Sequence[str],
        required_terms: Sequence[str] = (),
        forbidden_terms: Sequence[str] = (),
        fallback_model: Optional[str] = None,
    ) -> ModelRoutingReport:
        if not candidate_models:
            raise ValueError("at least one candidate model is required")
        memory = self._memory.search_memories(
            f"MODEL_POLICY task_family={task_family} selected model",
            container_tag=self._workspace_id,
            search_mode="memories",
            threshold=0.0,
            limit=5,
            rerank=False,
            rewrite_query=False,
        )
        text = json.dumps(memory, ensure_ascii=False, default=str)
        selected = self._select_from_memory(text, candidate_models)
        source = "supermemory-policy" if selected else "configured-fallback"
        memory_visible = selected is not None
        selected = selected or candidate_models[0]
        initial_model = selected
        initial_run = self._runner.run(selected, system_prompt, user_prompt)
        run = initial_run
        fallback_used = False
        output_valid = not required_terms or _terms_pass(
            initial_run.answer, required_terms, forbidden_terms
        )
        if not output_valid and fallback_model and fallback_model != selected:
            if fallback_model not in candidate_models:
                raise ValueError("fallback_model must be an allowed candidate")
            run = self._runner.run(fallback_model, system_prompt, user_prompt)
            selected = fallback_model
            fallback_used = True
            source += "+quality-fallback"
            self._memory.create_memories(
                self._workspace_id,
                [
                    {
                        "content": (
                            f"MODEL_POLICY_RUNTIME_FAILURE task_family={task_family} "
                            f"failed_model={initial_model} fallback_model={fallback_model} "
                            f"observed_at={_now()}. The selected model failed the required "
                            "output contract; prefer the verified fallback for this family "
                            "until recalibration."
                        ),
                        "isStatic": False,
                        "metadata": {
                            "kind": "model-routing-failure",
                            "taskFamily": task_family,
                            "failedModel": initial_model,
                            "fallbackModel": fallback_model,
                        },
                    }
                ],
            )
        return ModelRoutingReport(
            task_family=task_family,
            initial_model=initial_model,
            selected_model=selected,
            selection_source=source,
            memory_visible=memory_visible,
            fallback_used=fallback_used,
            initial_run=initial_run,
            run=run,
        )

    @staticmethod
    def _select_from_memory(text: str, candidate_models: Sequence[str]) -> Optional[str]:
        failed = set(re.findall(r"failed_model=([^\s.,;]+)", text))
        fallback = re.search(r"fallback_model=([^\s.,;]+)", text)
        if fallback and fallback.group(1) in candidate_models:
            return fallback.group(1)
        match = re.search(r"selected_model=([^\s.,;]+)", text)
        if match and match.group(1) in candidate_models and match.group(1) not in failed:
            return match.group(1)
        return next(
            (model for model in candidate_models if model in text and model not in failed),
            None,
        )
