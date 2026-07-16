"""Practical memory patterns that do not depend on a specific agent framework."""

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Protocol

from .context import render_profile_context, render_search_context
from .openrouter import LanguageModel


class MemoryBackend(Protocol):
    def profile(self, container_tag: str, **kwargs: Any) -> Dict[str, Any]:
        ...

    def add_conversation(
        self,
        conversation_id: str,
        messages: List[Mapping[str, Any]],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        ...

    def add_document(self, content: str, **kwargs: Any) -> Dict[str, Any]:
        ...

    def search_memories(
        self, query: str, **kwargs: Any
    ) -> Dict[str, Any]:
        ...

    def create_memories(
        self, container_tag: str, memories: List[Mapping[str, Any]]
    ) -> Dict[str, Any]:
        ...

    def update_memory(self, **kwargs: Any) -> Dict[str, Any]:
        ...


@dataclass(frozen=True)
class AgentTurn:
    answer: str
    retrieved_context: str
    persistence_error: Optional[str] = None


class PersonalizedAgent:
    """Profile-first agent with query recall and best-effort conversation storage."""

    def __init__(
        self,
        memory: MemoryBackend,
        llm: LanguageModel,
        *,
        instructions: str,
        retrieval_threshold: float = 0.55,
    ) -> None:
        self._memory = memory
        self._llm = llm
        self._instructions = instructions
        self._retrieval_threshold = retrieval_threshold
        self._history: Dict[str, List[Mapping[str, str]]] = {}

    def answer(
        self,
        *,
        user_id: str,
        conversation_id: str,
        message: str,
    ) -> AgentTurn:
        profile = self._memory.profile(
            user_id,
            query=message,
            threshold=self._retrieval_threshold,
            include=["static", "dynamic", "buckets"],
        )
        context = render_profile_context(profile)
        system = f"{self._instructions}\n\n{context}"
        answer = self._llm.complete(system, message)

        history = self._history.setdefault(conversation_id, [])
        history.extend(
            [
                {"role": "user", "content": message},
                {"role": "assistant", "content": answer},
            ]
        )
        persistence_error = None
        try:
            self._memory.add_conversation(
                conversation_id,
                history,
                container_tags=[user_id],
                metadata={"source": "personalized-agent"},
            )
        except Exception as error:  # Retrieval can be critical; writes are best effort.
            persistence_error = str(error)

        return AgentTurn(answer, context, persistence_error)


class ResearchNotebookAgent:
    """RAG-first notebook: raw sources stay citable and do not become user traits."""

    def __init__(
        self,
        memory: MemoryBackend,
        llm: LanguageModel,
        *,
        notebook_id: str,
    ) -> None:
        self._memory = memory
        self._llm = llm
        self._notebook_id = notebook_id

    def ingest_source(
        self,
        content: str,
        *,
        source_id: str,
        source_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {"sourceId": source_id, "kind": "research"}
        if source_url:
            metadata["sourceUrl"] = source_url
        return self._memory.add_document(
            content,
            container_tag=self._notebook_id,
            custom_id=source_id,
            metadata=metadata,
            task_type="superrag",
        )

    def answer(self, question: str) -> AgentTurn:
        results = self._memory.search_memories(
            question,
            container_tag=self._notebook_id,
            search_mode="hybrid",
            threshold=0.45,
            limit=8,
            rerank=True,
            include={"documents": True},
        )
        context = render_search_context(results)
        system = (
            "You are a research analyst. Answer only from retrieved evidence, cite "
            "the bracketed result numbers, and clearly label missing evidence.\n\n"
            f"{context}"
        )
        return AgentTurn(self._llm.complete(system, question), context)


class HandoffBoard:
    """A shared, searchable blackboard for a bounded team or workflow."""

    def __init__(self, memory: MemoryBackend, *, board_id: str) -> None:
        self._memory = memory
        self._board_id = board_id

    def publish(
        self,
        *,
        from_agent: str,
        task_id: str,
        fact: str,
        status: str = "open",
    ) -> Dict[str, Any]:
        content = f"Task {task_id}: {from_agent} reports {fact} (status: {status})"
        return self._memory.create_memories(
            self._board_id,
            [
                {
                    "content": content,
                    "isStatic": False,
                    "metadata": {
                        "kind": "handoff",
                        "fromAgent": from_agent,
                        "taskId": task_id,
                        "status": status,
                    },
                }
            ],
        )

    def recall(self, query: str) -> Dict[str, Any]:
        return self._memory.search_memories(
            query,
            container_tag=self._board_id,
            search_mode="memories",
            threshold=0.45,
            limit=20,
            aggregate=True,
        )


class DecisionJournal:
    """Store confirmed decisions directly and revise them with version history."""

    def __init__(self, memory: MemoryBackend, *, project_id: str) -> None:
        self._memory = memory
        self._project_id = project_id

    def record(self, decision: str, *, owner: str) -> Dict[str, Any]:
        return self._memory.create_memories(
            self._project_id,
            [
                {
                    "content": decision,
                    "isStatic": True,
                    "metadata": {"kind": "decision", "owner": owner},
                }
            ],
        )

    def revise(
        self, memory_id: str, new_decision: str, *, reason: str
    ) -> Dict[str, Any]:
        return self._memory.update_memory(
            memory_id=memory_id,
            new_content=new_decision,
            metadata={"kind": "decision", "revisionReason": reason},
        )

    def recall(self, question: str) -> Dict[str, Any]:
        return self._memory.search_memories(
            question,
            container_tag=self._project_id,
            search_mode="memories",
            threshold=0.5,
            include={"relatedMemories": True, "documents": True},
        )
