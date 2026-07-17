"""Run 120 live searches, select a policy, and use it in a recall agent."""

from dataclasses import asdict
from datetime import datetime, timezone
import json
import secrets

from supermemory_lab.config import load_config
from supermemory_lab.evaluation import RetrievalQuery, required_term_score
from supermemory_lab.live import build_live_clients
from supermemory_lab.retrieval_tuning import (
    RetrievalPolicy,
    RetrievalPolicyTuner,
    TunedRecallAgent,
)
from supermemory_lab.trace import RunTrace


from supermemory_lab.integrity import new_run_identity


_identity = new_run_identity


def main() -> None:
    identity = _identity()
    suffix = identity[-6:]
    container = f"lab:retrieval-grid:{identity}"
    policy_container = f"lab:retrieval-policy:{identity}"
    canary = f"RETRIEVAL_POLICY_{suffix}"
    selected = f"TRUSTED_GATE_{suffix}"
    distractors = (
        "Rejected candidate: broad repository mutation tool, OAuth required, unknown price, "
        "unbounded output, and no confirmation step. Another candidate sent email, changed "
        "deployment state, or executed arbitrary code and was rejected. "
    ) * 28
    content = (
        f"Evaluation record {canary}. The production requirement is to choose a memory policy "
        "for a public-data agent that retrieves prior tool decisions without treating them as "
        f"authorization. {distractors} Final decision {selected}: use explicit allowlists, "
        "re-inspect tool method/auth/price before every run, and keep code-level authorization "
        "outside retrieved memory."
    )
    queries = [
        RetrievalQuery("exact-canary", f"What record contains {canary}?", True),
        RetrievalQuery(
            "natural-task",
            "How should our public-data agent safely reuse its prior tool decisions?",
            True,
        ),
        RetrievalQuery(
            "semantic-paraphrase",
            "What guardrails did we choose for remembered integration recommendations?",
            True,
        ),
        RetrievalQuery(
            "unrelated-control",
            "What is the customer's approved maintenance window?",
            False,
        ),
        RetrievalQuery(
            "similar-distractor-control",
            "Which OAuth email mutation tool should autonomously send the invoice?",
            False,
        ),
    ]
    policies = [
        RetrievalPolicy(mode, threshold, rerank, rewrite)
        for mode in ("memories", "hybrid")
        for threshold in (0.0, 0.5, 0.7)
        for rerank in (False, True)
        for rewrite in (False, True)
    ]
    clients = build_live_clients(load_config())
    trace = RunTrace(
        f"retrieval-grid-{identity}", experiment="retrieval-policy-120-search-grid"
    )
    result = trace.capture(
        "run_retrieval_grid",
        "supermemory",
        lambda: RetrievalPolicyTuner(clients.memory).run(
            container_tag=container,
            content=content,
            canary=canary,
            queries=queries,
            policies=policies,
        ),
        summarize=lambda value: {
            "policyCount": value["policyCount"],
            "caseCount": value["caseCount"],
            "searchCount": value["searchCount"],
            "winner": value["winner"],
            "topFive": value["ranking"][:5],
            "cleanupErrors": value["cleanupErrors"],
        },
    )
    winner_values = result["winner"]["policy"]
    winner = RetrievalPolicy(
        search_mode=winner_values["search_mode"],
        threshold=winner_values["threshold"],
        rerank=winner_values["rerank"],
        rewrite_query=winner_values["rewrite_query"],
        limit=winner_values["limit"],
    )
    clients.memory.create_memories(
        policy_container,
        [
            {
                "content": (
                    f"Retrieval policy benchmark {identity}: selected {winner.name} from "
                    f"{result['policyCount']} policies and {result['searchCount']} searches. "
                    f"Metrics: {json.dumps(result['winner'], sort_keys=True)[:5000]}"
                ),
                "isStatic": False,
                "metadata": {
                    "kind": "retrieval-policy-benchmark",
                    "runId": identity,
                    "policy": winner.name,
                },
            }
        ],
    )

    # Recreate the benchmark fact so the selected policy is tested as an agent policy.
    created = clients.memory.create_memories(
        container,
        [{"content": content, "isStatic": False, "metadata": {"kind": "winner-agent-test"}}],
    )
    ids = [item.get("id") for item in created.get("memories", []) if isinstance(item, dict)]
    try:
        agent_report = trace.capture(
            "answer_with_winning_policy",
            "supermemory+openrouter",
            lambda: TunedRecallAgent(
                clients.memory,
                clients.llm,
                workspace_id=container,
                policy=winner,
                query_prefix=(
                    "public-data agent safely reuse prior tool decisions with explicit "
                    "allowlists and code-level authorization"
                ),
            ).answer("How must the public-data agent authorize remembered tool decisions?"),
            summarize=lambda value: {
                "answer": value.answer,
                "contextChars": len(value.retrieved_context),
                "retrievalQuery": value.retrieval_query,
                "policy": asdict(value.policy),
            },
        )
        answer_passed = required_term_score(
            agent_report.answer, ["allowlist", "authorization", "memory"]
        )
    finally:
        for memory_id in ids:
            if isinstance(memory_id, str):
                clients.memory.forget_memory(
                    container_tag=container,
                    memory_id=memory_id,
                    reason="winner agent test cleanup",
                )

    trace.metric("policyCount", result["policyCount"])
    trace.metric("searchCount", result["searchCount"])
    trace.metric("winner", result["winner"])
    trace.metric("topFive", result["ranking"][:5])
    trace.metric("winnerAgentAnswerPassed", answer_passed)
    trace.metric("policyMemoryContainer", policy_container)
    path = trace.write()
    print(
        json.dumps(
            {
                "trace": str(path),
                "winner": result["winner"],
                "answerPassed": answer_passed,
                "policyContainer": policy_container,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
