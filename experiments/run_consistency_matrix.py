"""Live direct-write visibility matrix across profile and search modes."""

from datetime import datetime, timezone
import json
import secrets

from supermemory_lab.config import load_config
from supermemory_lab.evaluation import ConsistencyMatrix, VisibilityCase
from supermemory_lab.live import build_live_clients
from supermemory_lab.trace import RunTrace


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    suffix = secrets.token_hex(3)
    run_id = f"consistency-{stamp}-{suffix}"
    clients = build_live_clients(load_config())
    matrix = ConsistencyMatrix(clients.memory)
    trace = RunTrace(run_id, experiment="direct-write-consistency-matrix")
    cases = [
        VisibilityCase(
            "short-static",
            f"Canary CONSISTENCY_SHORT_{suffix} belongs to the short static case.",
            True,
        ),
        VisibilityCase(
            "medium-dynamic",
            (
                f"Canary CONSISTENCY_MEDIUM_{suffix} belongs to a current workflow decision. "
                + "The decision includes evidence, owner, risk, rollback, and validation notes. "
                * 14
            ),
            False,
        ),
        VisibilityCase(
            "long-dynamic",
            (
                f"Canary CONSISTENCY_LONG_{suffix} belongs to a long tool-selection record. "
                + "Candidate capability, schema, authentication, price, mutation risk, rejection "
                "reason, selected version, expiry, and approval policy are recorded here. "
                * 45
            ),
            False,
        ),
    ]
    results = []
    for case in cases:
        canary = case.content.split()[1]
        result = trace.capture(
            f"measure_{case.name}",
            "supermemory",
            lambda case=case, canary=canary: matrix.run_case(
                case,
                container_tag=f"lab:consistency:{run_id}:{case.name}",
                canary=canary,
                timeout_seconds=60,
                poll_seconds=2,
            ),
            summarize=lambda value: value,
        )
        results.append(result)

    trace.metric("cases", results)
    path = trace.write()
    print(json.dumps({"trace": str(path), "results": results}, indent=2))


if __name__ == "__main__":
    main()
