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
PYTHONPATH=src python3 experiments/run_enterprise_context_agent.py
PYTHONPATH=src python3 experiments/run_corroborated_research_swarm.py
PYTHONPATH=src python3 experiments/run_adaptive_model_router.py
PYTHONPATH=src python3 experiments/run_temporal_agenda_agent.py
PYTHONPATH=src python3 experiments/run_dependency_risk_guardian.py
PYTHONPATH=src python3 experiments/run_governed_memory_curator.py
PYTHONPATH=src python3 experiments/run_resumable_agent_workcell.py
PYTHONPATH=src python3 experiments/run_relationship_account_briefing.py
PYTHONPATH=src python3 experiments/run_incident_forensics_agent.py
PYTHONPATH=src python3 experiments/run_tool_economics_portfolio.py
PYTHONPATH=src python3 experiments/run_graph_review_steward.py
PYTHONPATH=src python3 experiments/run_decision_council.py
PYTHONPATH=src python3 experiments/run_adaptive_tutor.py
PYTHONPATH=src python3 experiments/run_due_diligence_campaign.py
PYTHONPATH=src python3 experiments/run_change_risk_board.py
PYTHONPATH=src python3 experiments/run_retention_controller.py
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

`run_enterprise_context_agent.py` creates organization, project, user, and other-tenant scopes,
uses one multi-container key for the allowed hierarchy, verifies denial/revocation, and keeps
action permission in trusted code.

`run_corroborated_research_swarm.py` acquires a current official page, web and public-social
signals, writes source evidence, resists seeded memory injection, promotes only through a
deterministic fresh-source gate, and exercises a memory-only degraded cycle.

`run_adaptive_model_router.py` calibrates live OpenRouter models, persists the route policy,
injects a related-task contract failure, falls back, writes the outcome, and verifies that a
new process repairs its route.

`run_temporal_agenda_agent.py` tests exact and natural-language date windows with query rewriting
off/on, an unrelated negative, a bounded answer window, and complete cleanup.

`run_dependency_risk_guardian.py` discovers a price-capped exact-version CVE tool, reads official
and public evidence, tests the actual installed package in an egress-blocked sandbox, and writes
a verified lesson without authorizing production change.

`run_governed_memory_curator.py` retrieves correction evidence as untrusted data, quarantines
an unauthorized candidate, binds human approval to the exact replacement hash, rejects replay,
applies a versioned correction, and verifies current truth plus parent/root lineage.

`run_resumable_agent_workcell.py` signs planner/researcher/reviewer checkpoints, reconstructs
them in fresh processes, deduplicates an acknowledgement-loss retry, and rejects forged,
invalid-output, and backward-transition handoffs.

`run_relationship_account_briefing.py` batch-ingests consented CRM history with Dynamic
Dreaming, falls back to normalized direct facts if exact readiness times out, combines four
fresh public channels into a cited brief, and denies automated outreach in trusted code.

`run_incident_forensics_agent.py` keeps bounded read-only Vercel state separate from an
egress-blocked synthetic hypothesis rehearsal, persists only the passing lesson, and reports
production root cause as unknown when no logs exist.

`run_tool_economics_portfolio.py` executes the same public read task through Monid, Composio,
and Exa, treats non-comparable price as unknown rather than free, persists an expiring route
policy, and makes a new process revalidate the selected route.

`run_graph_review_steward.py` builds a three-version correction chain, audits the latest
entry's nested history and parent/root continuity, polls the inferred-review queue, rejects an
ordinary-memory review, and keeps approve/decline/undo behind exact external authorization.

`run_decision_council.py` asks three model families for independent schema-bound votes over an
immutable evidence manifest, requires exact citations and falsifiers, preserves invalid votes
and dissent, persists only a proposal, and rejects it when the evidence digest changes.

`run_adaptive_tutor.py` loads only signed mastery, applies deterministic decay and lesson-mode
selection, uses the model only to teach, verifies an assessment in an egress-blocked sandbox,
and versions mastery only from the verified grade.

`run_due_diligence_campaign.py` acquires a bounded public-source portfolio under call and cost
budgets, checkpoints it for fresh-process resume, tracks provider and publisher diversity,
requires exact citations, and withholds promotion in degraded or memory-only modes.

`run_change_risk_board.py` minimizes read-only deployment state, separates official guidance
from a synthetic staged-rollout rehearsal, lets current health override a passing sandbox, and
stores signed non-authoritative advice that becomes stale with the snapshot.

`run_retention_controller.py` partitions exact latest inventory by retention class, expiry,
legal hold, and review state; binds hold and deletion approvals to exact snapshots/plans;
rejects drift and replay; verifies absence; and emits canonical external audit events.
