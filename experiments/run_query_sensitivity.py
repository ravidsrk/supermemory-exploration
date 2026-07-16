"""Measure profile/search recall under exact, natural, paraphrased, and control queries."""

from datetime import datetime, timezone
import json
import secrets

from supermemory_lab.config import load_config
from supermemory_lab.evaluation import ConsistencyMatrix, RetrievalQuery
from supermemory_lab.live import build_live_clients
from supermemory_lab.trace import RunTrace


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    suffix = secrets.token_hex(3)
    run_id = f"query-sensitivity-{stamp}-{suffix}"
    canary = f"TOOL_DECISION_{suffix}"
    selected = f"READONLY_REPO_INSPECTOR_{suffix}"
    catalog = (
        "Candidate tool inventory: capability public repository inspection; visible schema; "
        "authentication OAuth; price unknown; mutation risk high; rejected because it changes "
        "collaborators or branch protection. "
    ) * 32
    content = (
        f"Tool-selection record {canary}. User request: find a read-only tool that inspects a "
        "public GitHub repository and summarizes recent issues, with visible schemas, predictable "
        f"cost, and no OAuth. {catalog} Final verified recommendation: {selected} is the chosen "
        "read-only candidate; never use mutation tools for this workflow."
    )
    queries = [
        RetrievalQuery("exact-canary", f"What record contains {canary}?", True),
        RetrievalQuery(
            "original-natural-language",
            "Find a read-only tool that can inspect a public GitHub repository and summarize recent issues. Prefer visible schemas, predictable cost, and no OAuth.",
            True,
        ),
        RetrievalQuery(
            "semantic-paraphrase",
            "Which safe integration did we choose for reviewing repository issue history?",
            True,
        ),
        RetrievalQuery("exact-tail-decision", f"Why was {selected} selected?", True),
        RetrievalQuery(
            "unrelated-control",
            "What is the customer's approved maintenance window?",
            False,
        ),
    ]
    clients = build_live_clients(load_config())
    trace = RunTrace(run_id, experiment="query-sensitivity-matrix")
    results = []
    for threshold, threshold_tag in ((0.0, "t0"), (0.5, "t05"), (0.7, "t07")):
        result = trace.capture(
            f"measure_query_sensitivity_{threshold}",
            "supermemory",
            lambda threshold=threshold: ConsistencyMatrix(
                clients.memory
            ).run_query_sensitivity(
                content=content,
                container_tag=f"lab:query-sensitivity:{run_id}:{threshold_tag}",
                canary=canary,
                queries=queries,
                threshold=threshold,
            ),
            summarize=lambda value: value,
        )
        results.append(result)
    trace.metric("results", results)
    path = trace.write()
    print(json.dumps({"trace": str(path), "results": results}, indent=2))


if __name__ == "__main__":
    main()
