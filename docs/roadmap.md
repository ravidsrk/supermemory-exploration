# Six-month exploration and adoption roadmap

Window: **2026-07-16 through 2027-01-16**. The goal is not to consume the free year by
integrating every surface. It is to turn six months of structured use into a reliable answer
about where Supermemory creates product leverage and where it should remain replaceable.

## Portfolio priorities

| Priority | Build | Why now | Success signal |
|---:|---|---|---|
| 1 | Personal/project profile assistant | Exercises the unique profile + dynamic fact model | Fewer repeated preferences/context questions without stale-fact increase |
| 2 | Cited research notebook | Exercises hybrid/SuperRAG and has low action risk | Supported-answer rate and time-to-find improve |
| 3 | Decision journal | Exercises direct facts and version graph | Current decision plus rationale retrieved reliably |
| 4 | Multi-agent handoff board | Tests aggregate context and shared workflow memory | Agents repeat fewer investigations; provenance retained |
| 5 | Coding historian | Daily real-world use and plugin comparison | Fewer rediscovered fixes/conventions across sessions |
| 6 | One connector-backed copilot | Validates managed-sync value | Sync/update/delete lifecycle passes and saves ingestion work |
| 7 | SMFS sandbox agent | Tests filesystem ergonomics | Agent uses fewer custom tools without consistency surprises |
| 8 | Self-hosted challenger | Preserves deployment leverage | Same domain suite passes backup/upgrade and acceptable quality |

Do not start with a high-stakes autonomous agent. Establish memory correctness on assistants
where a wrong recollection is visible and recoverable.

## Month 0: foundation — 2026-07-16 to 2026-07-31

Status: first pass complete in this repository.

Delivered:

- secure credential handling and a zero-dependency explicit API client;
- redacted hosted probes for core v3/v4, Router, and connector entitlement;
- fresh local-server and SMFS Bash tool validation;
- four tested agent primitives and a complete live demo;
- source-pinned SDK, plugin, MCP, SMFS, and MemoryBench inspection;
- practical wiki, production guardrails, evidence note, and benchmark plan.

Before month 1, rotate any credential that was pasted into an untrusted/public surface. Keep
all project keys out of git and use provider-specific least privilege where available.

## Month 1: turn observations into a domain baseline — August 2026

### Build

- Create the 100-question domain suite from [Benchmarks](benchmarks.md).
- Add a JSONL dataset schema with facts, updates, expected sources, forbidden tenants, and
  prompt-injection cases.
- Add repeatable result capture for quality, latency distribution, context tokens, and cost.
- Add scoped-key creation/revocation and cross-container denial tests.
- Exercise custom profile buckets, inference review, filter operators, rerank, rewrite, and
  `dreaming=dynamic`.

### Gate

- 100% deterministic tenant negative controls.
- 100% deleted-fact negative controls in the tested lifecycle.
- No retrieved instruction can cause an unauthorized tool action.
- Explicit p95 and context-token budgets agreed for each product path.

### Decision

Freeze one direct API/SDK version as the baseline. Do not adopt Router or a framework wrapper
as the only path yet.

## Month 2: personal assistant and research pilot — September 2026

### Build

- Ship a private profile-aware assistant to a small internal cohort.
- Add “what I remember,” edit, forget, and inferred-memory review.
- Ship the research notebook with source IDs, hybrid retrieval, and citation enforcement.
- Add application outbox/retry for conversation/document writes.
- Add explicit empty-memory versus memory-outage UX.

### Measure

- repeated-question rate;
- user corrections per 100 remembered facts;
- unsupported answer and stale-fact rate;
- retrieval p50/p95/p99 and end-to-end response latency;
- context tokens per successful task;
- user deletion/review completion.

### Stop conditions

- any cross-user leakage;
- sensitive inference without review;
- recurring stale facts that the update/delete model cannot correct;
- retrieval latency destroys the target interaction.

## Month 3: decisions, handoffs, and coding memory — October 2026

### Build

- Integrate the decision journal with one real project, keeping formal decisions in the
  existing system of record.
- Integrate the handoff board with one multi-agent workflow; keep queue/state transitions in
  the orchestrator.
- Compare official coding plugin behavior against the explicit project memory pattern.
- Add provenance links to commits, files, tickets, and source documents.

### Evaluate

- Can a new agent resume a task without rereading the entire transcript?
- Does aggregate retrieval save tokens without hiding contradictory underlying facts?
- Are failed approaches recalled when relevant, rather than repeatedly attempted?
- Does automatic coding capture create noise, private-data risk, or prompt injection?

### Gate

The workflow must remain correct when Supermemory is unavailable. Memory should improve
orientation, not own assignment or completion state.

## Month 4: connectors, SMFS, and self-hosted challenger — November 2026

### Hosted connector

Obtain entitlement for exactly one high-value provider. Test OAuth branding, resource
selection, initial sync, update, delete, revocation, ACL change, and container cleanup with
synthetic data before connecting real workspaces.

### SMFS

Pilot one sandbox workflow. Compare the real mount and virtual Bash tool on:

- cold start and semantic-search latency;
- multi-writer consistency;
- profile freshness;
- command compatibility;
- token/tool-call count;
- cleanup and container isolation.

### Self-hosted

Pin a server release. Run fresh install, restart durability, backup/restore, version upgrade,
large document, queue pressure, model outage, disk pressure, concurrency, and deletion tests.
Compare local extraction quality to hosted on the exact domain suite.

### Gate

No self-hosted production decision without a successful restore to a clean machine and an
upgrade rehearsal from the deployed version.

## Month 5: scale, economics, and provider challenge — December 2026

### Benchmark

- Run two public MemoryBench datasets with authorized direct judge credentials or a reviewed
  upstream OpenRouter adapter.
- Run the domain suite at realistic memory volume per user/project.
- Compare memories, hybrid, rerank, rewrite, and aggregate configurations.
- Compare at least one credible alternative or a simple RAG baseline on the same pipeline.

### Load and economics

- Measure ingest throughput, indexing lag, retrieval p95/p99, timeout rate, and context tokens.
- Calculate hosted cost per active user/task and self-hosted model/compute/operations cost.
- Test provider outage, throttling, and retry storms.
- Verify SDK retries cannot duplicate or multiply expensive writes.

### Gate

Choose by a workload-specific quality/latency/token/cost frontier, not a public accuracy
leaderboard.

## Month 6: production decision and hardening — January 1–16, 2027

Choose one of four outcomes per use case:

1. **Hosted direct API:** best when managed quality/connectors and rapid iteration win.
2. **Self-hosted:** best when residency/control wins and operations/quality gates pass.
3. **Replaceable adapter:** keep Supermemory behind the domain interface while evidence is mixed.
4. **Do not use memory here:** canonical lookup/full context/simple RAG is safer or cheaper.

For adopted paths, finish threat model, retention, deletion audit, incident runbook, SLOs,
budget alerts, version policy, and rollback. Record a decision journal entry with the evidence.

## Monthly recurring routine

On or near the 16th of each month:

1. Pull the official changelog, SDK releases, local-server releases, and relevant open issues.
2. Re-run unit tests, core hosted probe, Router probe, and domain smoke suite.
3. Record plan/region/model/version and client/server latency.
4. Inspect 20 sampled extracted facts and 20 sampled retrieved contexts.
5. Test one correction, precise deletion, and cross-tenant negative control.
6. Update the evidence note without erasing historical results.
7. Decide whether to upgrade, hold, or roll back.

## Scorecard

| Dimension | Target | Current first-pass status |
|---|---|---|
| Isolation | Zero negative-control leaks | Passed tiny hosted core and Router controls |
| Exact fact lifecycle | Create/update/forget works | Passed |
| Source retrieval | Correct chunk and citation | Passed synthetic text |
| Profile usefulness | Stable/dynamic are relevant | Passed synthetic facts; buckets pending |
| Cross-session Router | Recalls synthetic fact | Failed |
| Connector lifecycle | Sync/update/delete | Blocked by plan; entitlement only verified |
| Hosted retrieval p95 | Product-specific | Insufficient samples |
| Domain accuracy | Product-specific | Dataset pending |
| Prompt-injection resistance | No policy bypass | Renderer implemented; adversarial suite pending |
| Self-host durability | Restore and upgrade | Fresh run passed; durability/upgrade pending |
| SMFS maturity | Consistent read/search/profile | Read/search passed; profile/list quirks observed |

## Keep the integration replaceable

The `MemoryBackend` protocol in this repo is intentional. Product code should depend on
domain operations such as `recall_user`, `ingest_source`, `record_decision`, and
`forget_subject`, not on a framework wrapper scattered through model calls. That preserves
the ability to compare hosted, local, another provider, or a simpler implementation during
the free year without rewriting the agent.
