#!/usr/bin/env python3
"""Run the four practical agent patterns against isolated live containers.

This intentionally leaves the synthetic containers available for dashboard inspection.
Use only test content and delete the containers when the inspection is complete.
"""

import argparse
import json
import secrets
from typing import Any, Dict, Mapping

from supermemory_lab.agents import (
    DecisionJournal,
    HandoffBoard,
    PersonalizedAgent,
    ResearchNotebookAgent,
)
from supermemory_lab.client import SupermemoryClient
from supermemory_lab.config import load_config
from supermemory_lab.http import UrlLibTransport
from supermemory_lab.openrouter import OpenRouterClient


def build_clients(env_file: str) -> Any:
    config = load_config(env_file)
    memory = SupermemoryClient(
        UrlLibTransport(
            config.supermemory_base_url,
            config.supermemory_api_key,
            timeout_seconds=90,
        )
    )
    if not config.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required for the agent demos")
    llm = OpenRouterClient(
        UrlLibTransport(
            config.openrouter_base_url,
            config.openrouter_api_key,
            timeout_seconds=90,
        ),
        model=config.openrouter_model,
    )
    return memory, llm


def first_memory_id(response: Mapping[str, Any]) -> str:
    memories = response.get("memories")
    if not isinstance(memories, list) or not memories:
        raise RuntimeError("direct memory response had no memories")
    first = memories[0]
    memory_id = first.get("id") if isinstance(first, Mapping) else None
    if not isinstance(memory_id, str):
        raise RuntimeError("direct memory response had no memory ID")
    return memory_id


def run_personalized(memory: Any, llm: Any, container: str) -> Dict[str, Any]:
    memory.create_memories(
        container,
        [
            {"content": "The user prefers concise status updates.", "isStatic": True},
            {
                "content": "The Atlas prototype review is scheduled for Friday.",
                "isStatic": False,
            },
        ],
    )
    agent = PersonalizedAgent(
        memory,
        llm,
        instructions="Be a concise project chief of staff.",
    )
    turn = agent.answer(
        user_id=container,
        conversation_id=f"conversation:{container}",
        message="Give me the project reminder in my preferred style.",
    )
    return {"answer": turn.answer, "persistenceError": turn.persistence_error}


def run_research(memory: Any, llm: Any, container: str) -> Dict[str, Any]:
    agent = ResearchNotebookAgent(memory, llm, notebook_id=container)
    document = agent.ingest_source(
        (
            "The synthetic Northstar trial ran for six weeks. It reduced median "
            "retrieval time from 420 ms to 180 ms, but did not test concurrent writes."
        ),
        source_id=f"northstar-{container}",
        source_url="https://example.com/northstar-synthetic",
    )
    document_id = document.get("id")
    if not isinstance(document_id, str):
        raise RuntimeError("research ingestion returned no document ID")
    memory.wait_for_document(document_id, timeout_seconds=180)
    turn = agent.answer("What improved, and what remains untested?")
    return {"answer": turn.answer, "documentId": document_id}


def run_handoff(memory: Any, container: str) -> Dict[str, Any]:
    board = HandoffBoard(memory, board_id=container)
    board.publish(
        from_agent="researcher",
        task_id="northstar-42",
        fact="the latency result is source-backed, but concurrency remains untested",
        status="ready-for-review",
    )
    recalled = board.recall("What should the reviewer verify next?")
    return {"resultCount": len(recalled.get("results", [])), "recall": recalled}


def run_decision(memory: Any, container: str) -> Dict[str, Any]:
    journal = DecisionJournal(memory, project_id=container)
    created = journal.record("Use a 500 ms retrieval SLO for the pilot.", owner="demo-cto")
    original_id = first_memory_id(created)
    revised = journal.revise(
        original_id,
        "Use a 350 ms retrieval SLO for the pilot.",
        reason="Northstar synthetic trial",
    )
    recalled = journal.recall("What is the retrieval SLO and why did it change?")
    return {
        "originalMemoryId": original_id,
        "revisedMemoryId": revised.get("id"),
        "recall": recalled,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pattern",
        choices=("personalized", "research", "handoff", "decision", "all"),
        default="all",
    )
    parser.add_argument("--env-file", default=".env.local")
    args = parser.parse_args()
    memory, llm = build_clients(args.env_file)
    suffix = secrets.token_hex(3)
    selected = (
        ("personalized", "research", "handoff", "decision")
        if args.pattern == "all"
        else (args.pattern,)
    )
    output: Dict[str, Any] = {}
    for pattern in selected:
        container = f"lab:agent:{pattern}:{suffix}"
        print(f"Running {pattern} in {container}", flush=True)
        if pattern == "personalized":
            result = run_personalized(memory, llm, container)
        elif pattern == "research":
            result = run_research(memory, llm, container)
        elif pattern == "handoff":
            result = run_handoff(memory, container)
        else:
            result = run_decision(memory, container)
        output[pattern] = {"container": container, "result": result}
    print(json.dumps(output, indent=2, default=str))


if __name__ == "__main__":
    main()
