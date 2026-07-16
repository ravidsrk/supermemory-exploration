"""Reproducible hosted-API probes. Raw output is ignored until manually curated."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import secrets
import statistics
import time
from typing import Any, Callable, Dict, List, Mapping, Optional

from .agents import PersonalizedAgent
from .client import SupermemoryClient
from .config import LabConfig, load_config
from .http import JsonObject, UrlLibTransport
from .openrouter import OpenRouterClient
from .router import MemoryRouterClient


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _redact(value: Any, key: str = "") -> Any:
    lowered = key.lower()
    if lowered in {"key", "secret", "password"} or any(
        secret_key in lowered
        for secret_key in ("authorization", "api_key", "apikey", "token")
    ):
        return "[REDACTED]"
    if isinstance(value, Mapping):
        return {str(k): _redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value[:100]]
    if isinstance(value, str):
        return value[:4_000]
    return value


def _summarize_search(response: Mapping[str, Any]) -> JsonObject:
    results = response.get("results")
    results = results if isinstance(results, list) else []
    summarized: List[JsonObject] = []
    for result in results:
        if not isinstance(result, Mapping):
            continue
        text = result.get("memory") or result.get("chunk")
        context = result.get("context")
        context = context if isinstance(context, Mapping) else {}
        summarized.append(
            {
                "id": result.get("id"),
                "kind": "memory" if "memory" in result else "chunk" if "chunk" in result else "unknown",
                "text": text,
                "similarity": result.get("similarity"),
                "version": result.get("version"),
                "parentCount": len(context.get("parents", []))
                if isinstance(context.get("parents"), list)
                else 0,
                "childCount": len(context.get("children", []))
                if isinstance(context.get("children"), list)
                else 0,
            }
        )
    return {
        "timing": response.get("timing"),
        "total": response.get("total"),
        "resultCount": len(summarized),
        "results": summarized,
    }


def _summarize_document_search(response: Mapping[str, Any]) -> JsonObject:
    results = response.get("results")
    results = results if isinstance(results, list) else []
    summarized: List[JsonObject] = []
    for result in results:
        if not isinstance(result, Mapping):
            continue
        chunks = result.get("chunks")
        chunks = chunks if isinstance(chunks, list) else []
        summarized.append(
            {
                "documentId": result.get("documentId"),
                "score": result.get("score"),
                "chunkCount": len(chunks),
                "chunks": [
                    {
                        "content": chunk.get("content"),
                        "score": chunk.get("score"),
                        "isRelevant": chunk.get("isRelevant"),
                    }
                    for chunk in chunks[:3]
                    if isinstance(chunk, Mapping)
                ],
            }
        )
    return {
        "timing": response.get("timing"),
        "total": response.get("total"),
        "resultCount": len(summarized),
        "results": summarized,
    }


class ProbeRecorder:
    def __init__(self, run_id: str) -> None:
        self.report: JsonObject = {
            "schemaVersion": 1,
            "runId": run_id,
            "startedAt": _utc_now(),
            "observations": {},
        }

    def capture(
        self,
        name: str,
        action: Callable[[], Any],
        summarize: Optional[Callable[[Mapping[str, Any]], Any]] = None,
    ) -> Optional[Any]:
        start = time.perf_counter()
        try:
            raw = action()
            elapsed = round((time.perf_counter() - start) * 1000, 1)
            result = summarize(raw) if summarize and isinstance(raw, Mapping) else raw
            self.report["observations"][name] = {
                "status": "ok",
                "wallTimeMs": elapsed,
                "result": _redact(result),
            }
            print(f"[ok] {name} ({elapsed} ms)", flush=True)
            return raw
        except Exception as error:
            elapsed = round((time.perf_counter() - start) * 1000, 1)
            self.report["observations"][name] = {
                "status": "error",
                "wallTimeMs": elapsed,
                "errorType": type(error).__name__,
                "error": str(error)[:1_000],
            }
            print(f"[error] {name}: {type(error).__name__}", flush=True)
            return None

    def write(self) -> Path:
        self.report["finishedAt"] = _utc_now()
        output_dir = Path(".runs")
        output_dir.mkdir(exist_ok=True)
        path = output_dir / f"{self.report['runId']}.json"
        path.write_text(json.dumps(self.report, indent=2, sort_keys=True) + "\n")
        return path


def _build_clients(config: LabConfig) -> Any:
    memory_transport = UrlLibTransport(
        config.supermemory_base_url,
        config.supermemory_api_key,
        timeout_seconds=60,
    )
    return memory_transport, SupermemoryClient(memory_transport)


def run_core(config: LabConfig, *, with_llm: bool = False) -> Path:
    suffix = secrets.token_hex(3)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    run_id = f"core-{stamp}-{suffix}"
    container = f"lab:core:{stamp}:{suffix}"
    isolated_container = f"lab:isolation:{stamp}:{suffix}"
    transport, client = _build_clients(config)
    recorder = ProbeRecorder(run_id)
    recorder.report["containers"] = [container, isolated_container]

    direct = recorder.capture(
        "v4_create_exact_memories",
        lambda: client.create_memories(
            container,
            [
                {
                    "content": "Ravi's preferred programming language is Python.",
                    "isStatic": True,
                    "metadata": {"kind": "preference", "probe": run_id},
                },
                {
                    "content": "Ravi plans to launch Project Amber on 2026-08-15.",
                    "isStatic": False,
                    "metadata": {"kind": "project", "probe": run_id},
                },
                {
                    "content": "Ravi prefers concise weekly status updates.",
                    "isStatic": True,
                    "metadata": {"kind": "preference", "probe": run_id},
                },
            ],
        ),
    )

    memory_ids: List[str] = []
    if isinstance(direct, Mapping) and isinstance(direct.get("memories"), list):
        memory_ids = [
            item.get("id")
            for item in direct["memories"]
            if isinstance(item, Mapping) and isinstance(item.get("id"), str)
        ]

    recorder.capture(
        "v4_search_memories",
        lambda: client.search_memories(
            "When is Project Amber launching?",
            container_tag=container,
            search_mode="memories",
            threshold=0.0,
            include={"documents": True, "relatedMemories": True},
        ),
        _summarize_search,
    )
    recorder.capture(
        "v4_search_hybrid",
        lambda: client.search_memories(
            "preferred programming language and status style",
            container_tag=container,
            search_mode="hybrid",
            threshold=0.0,
        ),
        _summarize_search,
    )
    recorder.capture(
        "v4_search_default_mode_omitted",
        lambda: transport.request(
            "POST",
            "/v4/search",
            {
                "q": "Project Amber launch",
                "containerTag": container,
                "threshold": 0,
                "limit": 10,
            },
        ),
        _summarize_search,
    )
    recorder.capture(
        "v4_profile_with_search",
        lambda: client.profile(
            container,
            query="What should an assistant know about Ravi?",
            threshold=0.0,
            include=["static", "dynamic", "buckets"],
        ),
    )
    recorder.capture(
        "container_isolation_negative_control",
        lambda: client.search_memories(
            "Project Amber Python concise status",
            container_tag=isolated_container,
            search_mode="hybrid",
            threshold=0.0,
        ),
        _summarize_search,
    )

    if len(memory_ids) >= 2:
        recorder.capture(
            "v4_versioned_memory_update",
            lambda: client.update_memory(
                memory_id=memory_ids[1],
                container_tag=container,
                new_content="Ravi plans to launch Project Amber on 2026-09-01.",
                metadata={"kind": "project", "probe": run_id, "revision": 2},
            ),
        )
        recorder.capture(
            "v4_search_after_update",
            lambda: client.search_memories(
                "When is Project Amber launching?",
                container_tag=container,
                search_mode="memories",
                threshold=0.0,
                include={"relatedMemories": True, "documents": True},
            ),
            _summarize_search,
        )
        recorder.capture(
            "v4_forget_single_memory",
            lambda: client.forget_memory(
                container_tag=container,
                memory_id=memory_ids[0],
                reason="field-lab lifecycle probe",
            ),
        )
        recorder.capture(
            "v4_search_after_forget",
            lambda: client.search_memories(
                "preferred programming language",
                container_tag=container,
                search_mode="memories",
                threshold=0.0,
            ),
            _summarize_search,
        )

    recorder.capture(
        "v4_forget_matching_dry_run",
        lambda: client.forget_matching(
            "everything about Project Amber",
            container_tag=container,
            dry_run=True,
            threshold=0.0,
            max_forget=10,
        ),
    )

    document_content = (
        "Field Lab Memo. The Zephyr gateway uses port 7419. "
        "Its emergency rollback command is `zephyrctl retreat --safe`. "
        "The service owner is the Platform Reliability team. "
        "This synthetic document exists only to measure document retrieval, "
        "metadata propagation, and customId update behavior."
    )
    document = recorder.capture(
        "v3_add_document",
        lambda: client.add_document(
            document_content,
            container_tag=container,
            custom_id=f"field-lab-memo-{run_id}",
            metadata={"kind": "field-note", "probe": run_id, "version": 1},
            dreaming="instant",
        ),
    )
    document_id = document.get("id") if isinstance(document, Mapping) else None
    if isinstance(document_id, str):
        recorder.capture(
            "v3_wait_for_document",
            lambda: client.wait_for_document(document_id, timeout_seconds=180),
        )
        recorder.capture(
            "v3_document_search",
            lambda: client.search_documents(
                "What is the Zephyr rollback command and port?",
                container_tags=[container],
                chunk_threshold=0.0,
                document_threshold=0.0,
                include_summary=True,
            ),
            _summarize_document_search,
        )
        recorder.capture(
            "v4_hybrid_document_recall",
            lambda: client.search_memories(
                "Zephyr rollback command and gateway port",
                container_tag=container,
                search_mode="hybrid",
                threshold=0.0,
            ),
            _summarize_search,
        )
        recorder.capture(
            "v4_default_mode_with_document",
            lambda: transport.request(
                "POST",
                "/v4/search",
                {
                    "q": "Zephyr rollback command and gateway port",
                    "containerTag": container,
                    "threshold": 0,
                    "limit": 10,
                },
            ),
            _summarize_search,
        )
        upsert = recorder.capture(
            "v3_custom_id_upsert",
            lambda: client.add_document(
                document_content
                + " The verified incident channel is #zephyr-ops.",
                container_tag=container,
                custom_id=f"field-lab-memo-{run_id}",
                metadata={"kind": "field-note", "probe": run_id, "version": 2},
                dreaming="instant",
            ),
        )
        upsert_id = upsert.get("id") if isinstance(upsert, Mapping) else None
        if isinstance(upsert_id, str):
            recorder.capture(
                "v3_wait_for_upsert",
                lambda: client.wait_for_document(upsert_id, timeout_seconds=180),
            )
        recorder.capture(
            "v3_list_documents",
            lambda: client.list_documents(container_tags=[container], limit=20),
        )

    conversation_id = f"conversation-{run_id}"
    recorder.capture(
        "v4_structured_conversation_initial",
        lambda: client.add_conversation(
            conversation_id,
            [
                {"role": "user", "content": "I review plans on Monday mornings."},
                {"role": "assistant", "content": "I will keep Monday reviews in mind."},
            ],
            container_tags=[container],
            metadata={"probe": run_id, "kind": "conversation"},
        ),
    )
    recorder.capture(
        "v4_structured_conversation_append",
        lambda: client.add_conversation(
            conversation_id,
            [
                {"role": "user", "content": "I review plans on Monday mornings."},
                {"role": "assistant", "content": "I will keep Monday reviews in mind."},
                {"role": "user", "content": "Use a risk-first agenda for those reviews."},
                {"role": "assistant", "content": "Understood: risks first."},
            ],
            container_tags=[container],
            metadata={"probe": run_id, "kind": "conversation"},
        ),
    )

    latency_samples: List[float] = []
    for index in range(3):
        start = time.perf_counter()
        response = recorder.capture(
            f"v4_latency_sample_{index + 1}",
            lambda: client.search_memories(
                "Project Amber launch",
                container_tag=container,
                search_mode="memories",
                threshold=0.5,
                limit=5,
            ),
            _summarize_search,
        )
        if response is not None:
            latency_samples.append((time.perf_counter() - start) * 1000)
    if latency_samples:
        recorder.report["latencySummary"] = {
            "clientWallMedianMs": round(statistics.median(latency_samples), 1),
            "sampleCount": len(latency_samples),
        }

    if with_llm and config.openrouter_api_key:
        llm_transport = UrlLibTransport(
            config.openrouter_base_url,
            config.openrouter_api_key,
            timeout_seconds=90,
            extra_headers={
                "HTTP-Referer": "https://github.com/ravidsrk/supermemory-exploration",
                "X-Title": "Supermemory Field Lab",
            },
        )
        llm = OpenRouterClient(llm_transport, model=config.openrouter_model)
        agent = PersonalizedAgent(
            client,
            llm,
            instructions=(
                "You are a concise project chief of staff. Use recalled facts when "
                "relevant and explicitly say when memory lacks an answer."
            ),
        )
        recorder.capture(
            "end_to_end_personalized_agent",
            lambda: agent.answer(
                user_id=container,
                conversation_id=f"agent-{run_id}",
                message="Give me a two-line update covering my project date and communication preference.",
            ).__dict__,
        )
    elif with_llm:
        recorder.report["observations"]["end_to_end_personalized_agent"] = {
            "status": "skipped",
            "reason": "OpenRouter key not configured",
        }

    if isinstance(document_id, str):
        recorder.capture(
            "v3_delete_document_cleanup", lambda: client.delete_document(document_id)
        )
        recorder.capture(
            "v3_get_deleted_document_negative_control",
            lambda: client.get_document(document_id),
        )

    path = recorder.write()
    print(f"Raw secret-free run written to {path}", flush=True)
    return path


def run_web_crawler(config: LabConfig) -> Path:
    suffix = secrets.token_hex(3)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    run_id = f"web-crawler-{stamp}-{suffix}"
    container = f"lab:crawler:{stamp}:{suffix}"
    _, client = _build_clients(config)
    recorder = ProbeRecorder(run_id)
    recorder.report["containers"] = [container]

    connection = recorder.capture(
        "create_web_crawler_connection",
        lambda: client.create_connection(
            "web-crawler",
            container_tags=[container],
            metadata={"startUrl": "https://example.com", "probe": run_id},
            document_limit=1,
        ),
    )
    connection_id = connection.get("id") if isinstance(connection, Mapping) else None

    if isinstance(connection_id, str):
        documents: Optional[Mapping[str, Any]] = None
        for attempt in range(1, 13):
            documents = recorder.capture(
                f"crawler_documents_poll_{attempt}",
                lambda: client.list_connection_documents(
                    "web-crawler", container_tags=[container]
                ),
            )
            items = documents.get("data") if isinstance(documents, Mapping) else None
            if not isinstance(items, list) and isinstance(documents, Mapping):
                items = documents.get("documents")
            if isinstance(items, list) and items:
                break
            time.sleep(5)

        recorder.capture(
            "list_connections",
            lambda: client.list_connections(container_tags=[container]),
        )
        recorder.capture(
            "delete_web_crawler_connection",
            lambda: client.delete_connection(connection_id),
        )

        listed = recorder.capture(
            "list_crawler_documents_for_cleanup",
            lambda: client.list_documents(container_tags=[container], limit=20),
        )
        if isinstance(listed, Mapping) and isinstance(listed.get("memories"), list):
            for index, document in enumerate(listed["memories"], start=1):
                document_id = document.get("id") if isinstance(document, Mapping) else None
                if isinstance(document_id, str):
                    recorder.capture(
                        f"delete_crawler_document_{index}",
                        lambda document_id=document_id: client.delete_document(document_id),
                    )

    path = recorder.write()
    print(f"Raw secret-free run written to {path}", flush=True)
    return path


def run_memory_router(config: LabConfig) -> Path:
    if not config.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required for the Router probe")

    suffix = secrets.token_hex(3)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    run_id = f"memory-router-{stamp}-{suffix}"
    user_id = f"lab-router-user-{stamp}-{suffix}"
    conversation_id = f"lab-router-conversation-{stamp}-{suffix}"
    other_user_id = f"lab-router-negative-{stamp}-{suffix}"
    recorder = ProbeRecorder(run_id)
    recorder.report["subjects"] = [user_id, other_user_id]
    _, memory = _build_clients(config)
    router = MemoryRouterClient(
        supermemory_api_key=config.supermemory_api_key,
        provider_api_key=config.openrouter_api_key,
        provider_base_url=config.openrouter_base_url,
        model=config.openrouter_model,
    )

    recorder.capture(
        "router_initial_fact",
        lambda: router.complete(
            user_id=user_id,
            conversation_id=conversation_id,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "For this synthetic field-lab conversation, remember that "
                        "the audit code phrase is cobalt lighthouse. Reply only with "
                        "a short acknowledgement."
                    ),
                }
            ],
        ),
    )
    time.sleep(20)
    recorder.capture(
        "router_same_user_continuation",
        lambda: router.complete(
            user_id=user_id,
            conversation_id=conversation_id,
            messages=[
                {
                    "role": "user",
                    "content": "What was the synthetic audit code phrase?",
                }
            ],
        ),
    )
    recorder.capture(
        "router_same_user_new_conversation",
        lambda: router.complete(
            user_id=user_id,
            conversation_id=f"new-{conversation_id}",
            messages=[
                {
                    "role": "user",
                    "content": "What was the synthetic audit code phrase?",
                }
            ],
        ),
    )
    recorder.capture(
        "router_full_history_control",
        lambda: router.complete(
            user_id=user_id,
            conversation_id=f"full-{conversation_id}",
            messages=[
                {
                    "role": "user",
                    "content": (
                        "For this synthetic field-lab conversation, remember that "
                        "the audit code phrase is cobalt lighthouse."
                    ),
                },
                {"role": "assistant", "content": "Acknowledged."},
                {
                    "role": "user",
                    "content": "What was the synthetic audit code phrase?",
                },
            ],
        ),
    )
    recorder.capture(
        "router_memory_api_visibility",
        lambda: memory.search_memories(
            "synthetic audit code phrase",
            container_tag=user_id,
            search_mode="hybrid",
            threshold=0.0,
        ),
        _summarize_search,
    )
    recorder.capture(
        "router_other_user_negative_control",
        lambda: router.complete(
            user_id=other_user_id,
            conversation_id=f"negative-{conversation_id}",
            messages=[
                {
                    "role": "user",
                    "content": (
                        "What is the synthetic audit code phrase? If you have no "
                        "context for it, say unknown."
                    ),
                }
            ],
        ),
    )

    path = recorder.write()
    print(f"Raw secret-free run written to {path}", flush=True)
    return path


def run_scoped_key(config: LabConfig) -> Path:
    suffix = secrets.token_hex(3)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    run_id = f"scoped-key-{stamp}-{suffix}"
    allowed = f"lab:scoped:allowed:{stamp}:{suffix}"
    denied = f"lab:scoped:denied:{stamp}:{suffix}"
    _, admin = _build_clients(config)
    recorder = ProbeRecorder(run_id)
    recorder.report["containers"] = [allowed, denied]

    seed_allowed = recorder.capture(
        "admin_seed_allowed_container",
        lambda: admin.create_memories(
            allowed,
            [
                {
                    "content": "The scoped-key canary color is ultraviolet.",
                    "isStatic": True,
                    "metadata": {"probe": run_id},
                }
            ],
        ),
    )
    seed_denied = recorder.capture(
        "admin_seed_denied_container",
        lambda: admin.create_memories(
            denied,
            [
                {
                    "content": "The denied-container canary color is infrared.",
                    "isStatic": True,
                    "metadata": {"probe": run_id},
                }
            ],
        ),
    )
    scoped = recorder.capture(
        "create_container_scoped_key",
        lambda: admin.create_scoped_key(
            allowed,
            name=f"field-lab-{suffix}",
            expires_in_days=1,
            rate_limit_max=100,
            rate_limit_time_window=60_000,
        ),
    )
    scoped_key = scoped.get("key") if isinstance(scoped, Mapping) else None
    scoped_key_id = scoped.get("id") if isinstance(scoped, Mapping) else None
    scoped_client: Optional[SupermemoryClient] = None
    scoped_write: Optional[Any] = None

    if isinstance(scoped_key, str):
        scoped_client = SupermemoryClient(
            UrlLibTransport(
                config.supermemory_base_url,
                scoped_key,
                timeout_seconds=60,
            )
        )
        recorder.capture(
            "scoped_read_allowed_container",
            lambda: scoped_client.search_memories(
                "scoped-key canary color",
                container_tag=allowed,
                search_mode="memories",
                threshold=0.0,
            ),
            _summarize_search,
        )
        recorder.capture(
            "scoped_read_denied_container",
            lambda: scoped_client.search_memories(
                "denied-container canary color",
                container_tag=denied,
                search_mode="memories",
                threshold=0.0,
            ),
            _summarize_search,
        )
        scoped_write = recorder.capture(
            "scoped_write_allowed_container",
            lambda: scoped_client.create_memories(
                allowed,
                [
                    {
                        "content": "Scoped writes are allowed in the bound container.",
                        "isStatic": True,
                        "metadata": {"probe": run_id},
                    }
                ],
            ),
        )
        recorder.capture(
            "scoped_write_denied_container",
            lambda: scoped_client.create_memories(
                denied,
                [
                    {
                        "content": "This cross-container write must be rejected.",
                        "isStatic": True,
                        "metadata": {"probe": run_id},
                    }
                ],
            ),
        )

    if isinstance(scoped_key_id, str):
        recorder.capture(
            "revoke_container_scoped_key",
            lambda: admin.revoke_scoped_key(scoped_key_id),
        )
    if scoped_client is not None:
        recorder.capture(
            "revoked_key_negative_control",
            lambda: scoped_client.search_memories(
                "scoped-key canary color",
                container_tag=allowed,
                search_mode="memories",
                threshold=0.0,
            ),
            _summarize_search,
        )

    seen_ids = set()
    for container_tag, response in (
        (allowed, seed_allowed),
        (denied, seed_denied),
        (allowed, scoped_write),
    ):
        memories = response.get("memories") if isinstance(response, Mapping) else None
        if not isinstance(memories, list):
            continue
        for item in memories:
            memory_id = item.get("id") if isinstance(item, Mapping) else None
            if not isinstance(memory_id, str) or memory_id in seen_ids:
                continue
            seen_ids.add(memory_id)
            recorder.capture(
                f"cleanup_memory_{len(seen_ids)}",
                lambda memory_id=memory_id, container_tag=container_tag: admin.forget_memory(
                    container_tag=container_tag,
                    memory_id=memory_id,
                    reason="field-lab scoped-key cleanup",
                ),
            )

    path = recorder.write()
    print(f"Raw secret-free run written to {path}", flush=True)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--with-llm", action="store_true", help="also run an OpenRouter-backed agent"
    )
    parser.add_argument(
        "--with-connector",
        action="store_true",
        help="also exercise the no-OAuth web-crawler connector",
    )
    parser.add_argument(
        "--connector-only",
        action="store_true",
        help="run only the no-OAuth web-crawler connector probe",
    )
    parser.add_argument(
        "--with-router",
        action="store_true",
        help="exercise the OpenAI-compatible Memory Router via OpenRouter",
    )
    parser.add_argument(
        "--router-only",
        action="store_true",
        help="run only the OpenRouter-backed Memory Router probe",
    )
    parser.add_argument(
        "--with-scoped-key",
        action="store_true",
        help="exercise container-scoped key enforcement and revocation",
    )
    parser.add_argument(
        "--scoped-key-only",
        action="store_true",
        help="run only the container-scoped key security probe",
    )
    parser.add_argument("--env-file", default=".env.local")
    args = parser.parse_args()
    config = load_config(args.env_file)
    if not args.connector_only and not args.router_only and not args.scoped_key_only:
        run_core(config, with_llm=args.with_llm)
    if args.with_connector or args.connector_only:
        run_web_crawler(config)
    if args.with_router or args.router_only:
        run_memory_router(config)
    if args.with_scoped_key or args.scoped_key_only:
        run_scoped_key(config)


if __name__ == "__main__":
    main()
