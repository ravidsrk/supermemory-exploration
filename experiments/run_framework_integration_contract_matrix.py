"""Run all framework/MCP/plugin contracts without external provider mutations."""

from typing import Any, Dict, Mapping, Sequence

from supermemory_lab.authorization import TestingAuthorizationLedger
from supermemory_lab.framework_integrations import (
    FRAMEWORK_CONTRACTS,
    MemoryIntegrationBridge,
)
from supermemory_lab.integrity import new_run_identity
from supermemory_lab.trace import RunTrace


class ContractMemory:
    def __init__(self) -> None:
        self.profile_scopes = []
        self.conversation_scopes = []
        self.writes = []

    def profile(self, container_tag: str, **kwargs: Any) -> Dict[str, Any]:
        self.profile_scopes.append(container_tag)
        return {
            "profile": {"static": ["Synthetic contract preference: concise answers"]}
        }

    def add_conversation(
        self,
        conversation_id: str,
        messages: Sequence[Mapping[str, Any]],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        self.conversation_scopes.extend(kwargs.get("container_tags") or [])
        return {"id": conversation_id, "accepted": True}

    def create_memories(self, container_tag: str, memories: Sequence[Mapping[str, Any]]):
        self.writes.extend(memories)
        return {"memories": [{"id": "synthetic-memory"}]}


def main() -> None:
    identity = new_run_identity()
    tenant = f"lab:framework-contract:{identity}"
    memory = ContractMemory()
    ledger = TestingAuthorizationLedger()
    bridge = MemoryIntegrationBridge(
        memory,
        container_tag=tenant,
        custom_id=f"conversation:{identity}",
        authorization_ledger=ledger,
    )
    trace = RunTrace(
        f"framework-contracts-{identity}",
        experiment="framework-mcp-plugin-contract-matrix",
    )
    results = []
    for contract in FRAMEWORK_CONTRACTS:
        config = bridge.framework_config(contract.surface)
        context = bridge.before_turn(contract.surface, "What response style is preferred?")
        capture = bridge.after_turn(
            contract.surface,
            [
                {"role": "user", "content": "What style should you use?"},
                {"role": "assistant", "content": "A concise style."},
            ],
        )
        results.append(
            {
                "surface": contract.surface,
                "style": config["style"],
                "failOpen": config["failOpen"],
                "boundedContext": len(context) <= 6_000,
                "closedBoundary": context.endswith("</retrieved-memory>"),
                "captured": capture.get("accepted") is True,
            }
        )
    denied = False
    try:
        bridge.invoke_memory_tool("Unapproved synthetic write", actor="synthetic-operator")
    except PermissionError:
        denied = True
    evaluation = {
        "surfaceCount": len(results),
        "expectedSurfaceCount": len(FRAMEWORK_CONTRACTS),
        "allFailClosed": all(item["failOpen"] is False for item in results),
        "allContextsBounded": all(item["boundedContext"] for item in results),
        "allBoundariesClosed": all(item["closedBoundary"] for item in results),
        "allCapturesAccepted": all(item["captured"] for item in results),
        "allScopesExact": set(memory.profile_scopes + memory.conversation_scopes) == {tenant},
        "unauthorizedWriteDenied": denied,
    }
    evaluation["passed"] = all(
        value is True
        for key, value in evaluation.items()
        if key not in {"surfaceCount", "expectedSurfaceCount", "passed"}
    ) and evaluation["surfaceCount"] == evaluation["expectedSurfaceCount"]
    trace.metric("contracts", results)
    trace.metric("evaluation", evaluation)
    path = trace.write()
    print({"trace": str(path), "evaluation": evaluation})


if __name__ == "__main__":
    main()
