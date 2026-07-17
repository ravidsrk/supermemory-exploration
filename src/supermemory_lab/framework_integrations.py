"""Runnable contracts for framework, MCP, plugin, and Convex integrations.

The adapters intentionally depend only on the field-lab memory protocol. Third-party
framework code can call these hooks without making framework packages dependencies of
the core lab.
"""

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Protocol, Sequence, Tuple

from .authorization import (
    AuthorizationLedger,
    authorization_resource,
    consume_authorization,
)
from .context import render_profile_context


class IntegrationMemory(Protocol):
    def profile(self, container_tag: str, **kwargs: Any) -> Dict[str, Any]: ...

    def add_conversation(
        self,
        conversation_id: str,
        messages: Sequence[Mapping[str, Any]],
        **kwargs: Any,
    ) -> Dict[str, Any]: ...

    def create_memories(
        self, container_tag: str, memories: Sequence[Mapping[str, Any]]
    ) -> Dict[str, Any]: ...


@dataclass(frozen=True)
class FrameworkContract:
    surface: str
    integration_style: str
    retrieval_hook: str
    persistence_hook: str
    requires_custom_id: bool = True


FRAMEWORK_CONTRACTS: Tuple[FrameworkContract, ...] = (
    FrameworkContract("vercel-ai-sdk", "withSupermemory", "model middleware", "response capture"),
    FrameworkContract("openai-agents", "function tools", "agent instructions", "post-run capture"),
    FrameworkContract("langchain", "runnable hooks", "pre-invoke", "post-invoke"),
    FrameworkContract("langgraph", "graph nodes", "recall node", "persist node"),
    FrameworkContract("mastra", "withSupermemory", "input processor", "output processor"),
    FrameworkContract("agno", "agent context", "pre-run", "post-run"),
    FrameworkContract("crewai", "crew context", "pre-kickoff", "post-kickoff"),
    FrameworkContract("convex", "server actions", "query action", "mutation action"),
    FrameworkContract("mcp", "tools/resources/prompt", "recall/context", "memory tool"),
    FrameworkContract("coding-plugin", "session hooks", "session start", "session end"),
)
_BY_SURFACE = {contract.surface: contract for contract in FRAMEWORK_CONTRACTS}


class MemoryIntegrationBridge:
    """One tenant-safe recall/capture boundary shared by every framework adapter."""

    def __init__(
        self,
        memory: IntegrationMemory,
        *,
        container_tag: str,
        custom_id: str,
        authorization_ledger: AuthorizationLedger,
        max_context_chars: int = 6_000,
    ) -> None:
        if not container_tag.strip() or not custom_id.strip():
            raise ValueError("container_tag and custom_id are required stable identifiers")
        if max_context_chars < 512:
            raise ValueError("max_context_chars must preserve the safety frame")
        self._memory = memory
        self._authorization_ledger = authorization_ledger
        self.container_tag = container_tag
        self.custom_id = custom_id
        self._max_context_chars = max_context_chars

    @staticmethod
    def contract(surface: str) -> FrameworkContract:
        try:
            return _BY_SURFACE[surface]
        except KeyError as error:
            raise ValueError(f"unknown integration surface: {surface}") from error

    def framework_config(self, surface: str) -> Mapping[str, Any]:
        contract = self.contract(surface)
        base: Dict[str, Any] = {
            "surface": contract.surface,
            "style": contract.integration_style,
            "containerTag": self.container_tag,
            "customId": self.custom_id,
            "retrievalHook": contract.retrieval_hook,
            "persistenceHook": contract.persistence_hook,
            "failOpen": False,
        }
        if surface in {"vercel-ai-sdk", "mastra"}:
            base.update({"mode": "full", "skipMemoryOnError": False, "addMemory": "always"})
        elif surface == "mcp":
            base.update(
                {
                    "serverUrl": "https://mcp.supermemory.ai/mcp",
                    "tools": ("memory", "recall"),
                    "resources": ("supermemory://profile", "supermemory://projects"),
                    "prompts": ("context",),
                }
            )
        elif surface == "coding-plugin":
            base.update(
                {
                    "hooks": ("sessionStart", "userPromptSubmit", "sessionEnd"),
                    "scopes": ("user", "project", "custom"),
                }
            )
        elif surface == "convex":
            base.update({"readOperation": "action", "writeOperation": "mutation"})
        return base

    def before_turn(self, surface: str, query: str) -> str:
        self.contract(surface)
        if not query.strip():
            raise ValueError("integration recall query is required")
        response = self._memory.profile(
            self.container_tag,
            query=query,
            threshold=0.0,
            include=["static", "dynamic", "buckets"],
        )
        return render_profile_context(response, max_chars=self._max_context_chars)

    def after_turn(
        self, surface: str, messages: Sequence[Mapping[str, Any]]
    ) -> Mapping[str, Any]:
        self.contract(surface)
        normalized = tuple(
            {"role": str(item.get("role") or ""), "content": str(item.get("content") or "")}
            for item in messages
        )
        if not normalized or any(
            item["role"] not in {"user", "assistant"} or not item["content"].strip()
            for item in normalized
        ):
            raise ValueError("captured turns require non-empty user/assistant messages")
        return self._memory.add_conversation(
            self.custom_id,
            normalized,
            container_tags=[self.container_tag],
            metadata={"integrationSurface": surface, "kind": "framework-conversation"},
        )

    @staticmethod
    def mcp_tool_schemas() -> Mapping[str, Mapping[str, Any]]:
        return {
            "recall": {
                "description": "Search tenant-scoped memory",
                "inputSchema": {
                    "type": "object",
                    "required": ["query"],
                    "properties": {"query": {"type": "string"}},
                    "additionalProperties": False,
                },
            },
            "memory": {
                "description": "Save one explicitly authorized memory",
                "inputSchema": {
                    "type": "object",
                    "required": ["content"],
                    "properties": {"content": {"type": "string"}},
                    "additionalProperties": False,
                },
            },
        }

    def memory_write_resource(self, content: str) -> str:
        """Return the exact resource hash an external authority must grant."""

        if not content.strip():
            raise ValueError("memory tool content is required")
        return authorization_resource(
            "integration.memory.create", self.container_tag, content
        )

    def invoke_memory_tool(self, content: str, *, actor: str) -> Mapping[str, Any]:
        resource_hash = self.memory_write_resource(content)
        consume_authorization(
            self._authorization_ledger,
            scope="integration.memory.create",
            actor=actor,
            resource_hash=resource_hash,
        )
        return self._memory.create_memories(
            self.container_tag,
            [
                {
                    "content": content,
                    "isStatic": False,
                    "metadata": {"kind": "explicit-integration-memory"},
                }
            ],
        )
