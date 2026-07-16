# Experiments

Experiments are opt-in and use isolated container tags prefixed with `lab:`. Raw run output goes to ignored `.runs/`; only manually reviewed, secret-free summaries belong in `evidence/`.

```bash
PYTHONPATH=src python3 -m supermemory_lab.probes
PYTHONPATH=src python3 -m supermemory_lab.probes --with-llm
PYTHONPATH=src python3 -m supermemory_lab.probes --connector-only
PYTHONPATH=src python3 -m supermemory_lab.probes --router-only
PYTHONPATH=src python3 -m supermemory_lab.probes --scoped-key-only
PYTHONPATH=src python3 experiments/run_safe_tool_execution.py
PYTHONPATH=src python3 experiments/run_governance_scorecard.py
PYTHONPATH=src python3 experiments/run_signal_radar.py
PYTHONPATH=src python3 experiments/run_retrieval_policy_grid.py
PYTHONPATH=src python3 experiments/run_release_triage_rehearsal.py
PYTHONPATH=src python3 experiments/run_evolving_preference_agent.py
PYTHONPATH=src python3 experiments/run_filter_erasure_agent.py
PYTHONPATH=src python3 experiments/run_lifecycle_agents.py
PYTHONPATH=src python3 experiments/run_router_continuity_matrix.py
PYTHONPATH=src python3 experiments/run_domain_memory_benchmark.py
```

The core probe exercises:

- v4 direct memory creation, search, profile, versioned update, and forgetting
- strict container isolation
- the undocumented/default search-mode question
- v3 document ingestion, processing, search, `customId` upsert, listing, and deletion
- v4 structured conversation ingestion
- optional profile-aware agent generation through OpenRouter
- optional OpenRouter-backed Memory Router continuation and isolation checks
- optional scoped-key read/write isolation, revocation, and cleanup checks

Do not paste raw run files into bug reports without reviewing them first. They contain synthetic experiment content and hosted resource IDs, but the redactor intentionally errs on the side of preserving useful response evidence.

`run_safe_tool_execution.py` performs real calls, but only after fail-closed checks:
the Monid tool must be explicitly allowlisted, inspect as `GET`, and cost no more than
the configured cap; the Composio tool must be explicitly allowlisted, report `no_auth`,
and contain no mutation verb token. Public results are stored as untrusted SuperRAG
documents, while the verified execution policy is stored as a direct dynamic memory.

`run_governance_scorecard.py` runs 15 synthetic cases: three versioned corrections,
three precise-forget cases with retained controls, four tenant-isolation pairs, and five
attacker-controlled document payloads. It checks profile, memories, and hybrid reads. The
injection agent can answer from retrieved facts, but authorization is always decided by
trusted application code and remains false regardless of model output.

`run_signal_radar.py` combines a no-auth Hacker News search through Composio, Exa web
search, ScrapeCreators Reddit/X reads, OpenRouter synthesis, and Supermemory history. It
then repeats the briefing with external refresh disabled to measure a cheaper memory-only
continuity/degraded mode without claiming that remembered evidence is current.

`run_retrieval_policy_grid.py` makes 120 live v4 searches across 24 combinations of
search mode, threshold, reranking, and query rewriting. Five exact, semantic, unrelated,
and deceptively similar queries score recall and false positives alongside p50/p95 latency
and payload size. The winning policy is stored as a dated dynamic memory and immediately
used by a recall agent; benchmark content is precisely forgotten after the run.

`run_release_triage_rehearsal.py` combines read-only Vercel state, a static Supermemory
security runbook, OpenRouter patch generation, and an egress-blocked disposable SuperServe
sandbox. It begins with a deliberately failing webhook verifier and stores the lesson only
after tests pass. Vercel observations and sandbox results remain explicitly separate: a
synthetic rehearsal is never presented as diagnosis of a real deployment.

`run_evolving_preference_agent.py` archives a role-preserving conversation, explicitly
normalizes confirmed preferences, versions corrections, configures custom buckets, checks
idempotency and isolation, and deletes the synthetic container. It does not assume completed
conversation processing has already produced the needed profile fact.

`run_filter_erasure_agent.py` evaluates seven v4 search-filter shapes and requires a bounded
dry-run candidate set before semantic erasure. Protected canaries, candidate drift, excessive
cardinality, and unexpected empty previews fail closed.

`run_lifecycle_agents.py` gives a temporary incident fact server-enforced expiry, cancels a
second expiry through versioned update, and consolidates two synthetic workspaces through the
queued merge state machine while verifying data, settings, source removal, and cleanup.

`run_router_continuity_matrix.py` separates delta-only model continuity, explicit full history,
direct API memory-pool injection, another-user isolation, Router-generated cross-session
recall, response diagnostics, token counts, API visibility, and cleanup.

`run_domain_memory_benchmark.py` runs 12 paired memory/no-memory questions across stable,
update, temporal, multi-hop, isolation, and prompt-injection categories. It separately scores
retrieval canaries and answer semantics, reports p50/p95 search latency and bounded context,
and requires zero leaks/bypasses before passing.
