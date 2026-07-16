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

Status: foundation and expanded multi-provider pass complete in this repository.

Delivered:

- secure credential handling and a zero-dependency explicit API client;
- redacted hosted probes for core v3/v4, Router, and connector entitlement;
- fresh local-server and SMFS Bash tool validation;
- four tested agent primitives and a complete live demo;
- five additional multi-provider agents using every supplied provider credential;
- five memory-native systems for enterprise hierarchy, corroboration, adaptive model routing,
  temporal recall, and dependency risk;
- five operational systems for governed correction, signed restart recovery, consent-aware
  account briefing, incident-hypothesis falsification, and read-tool economics;
- six deep systems for graph/review stewardship, multi-model evidence deliberation,
  assessment-verified tutoring, budgeted resumable due diligence, change-risk simulation, and
  legal-hold-aware retention;
- five deep operational implementations for actual-inventory transparency/erasure, contract
  drift, signed long-horizon project state, valid-dissent preservation, and resumable migration,
  plus a larger matched Dreaming/review matrix;
- a causal sandbox transfer test where memory passed and the stateless candidate failed;
- a three-case support benchmark scoring 3/3 with memory and 0/3 without it;
- profile-versus-search read-after-write evidence and explicit polling barriers;
- source-pinned SDK, plugin, MCP, SMFS, and MemoryBench inspection;
- custom profile buckets, seven search-filter shapes, memory expiry/cancellation, inferred
  review endpoint/empty queue/ordinary-memory 409, three-version nested history, and queued
  container merge lifecycle;
- a correction-aware conversation-plus-direct-fact agent and preview-gated erasure agent;
- a 12-case matched domain smoke suite scoring 12/12 with memory versus 2/12 without;
- a Router continuity matrix separating model history, direct memory pool, tenant isolation,
  and Router-generated cross-session persistence;
- practical wiki, production guardrails, evidence note, and benchmark plan.

Before month 1, rotate any credential that was pasted into an untrusted/public surface. Keep
all project keys out of git and use provider-specific least privilege where available.

## Month 1: turn observations into a domain baseline — August 2026

### Build

- Create the 100-question domain suite from [Benchmarks](benchmarks.md).
- Grow the completed 12-case executable smoke slice into that blinded 100-question suite.
- Add a JSONL dataset schema with facts, updates, expected sources, forbidden tenants, and
  prompt-injection cases.
- Add repeatable result capture for quality, latency distribution, context tokens, and cost.
- Expand the passing single- and multi-container scoped-key probes with endpoint and rate-limit
  cases.
- Complete approve/decline/undo on a qualifying generated inference. Custom profile buckets,
  filter operators, rerank/rewrite, expiry, merge, batch ingestion, both Dreaming modes, and
  one non-deterministic one-parent candidate observation now have executable coverage. Repeat
  at larger scale and instrument the queue/readiness gap.

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
8. Exercise one degraded dependency/provider path and verify the agent labels partial state,
   preserves failures, and withholds promotion or action.

## Scorecard

| Dimension | Target | Current first-pass status |
|---|---|---|
| Isolation | Zero negative-control leaks | Passed container, Router-user, and scoped-key read/write controls |
| Exact fact lifecycle | Create/update/forget works | Passed |
| Source retrieval | Correct chunk and citation | Passed synthetic text |
| Profile usefulness | Stable/dynamic are relevant | Passed synthetic facts and custom bucket classification |
| Cross-session Router | Recalls synthetic fact | Direct API pool passed; Router-generated new-conversation recall failed |
| Connector lifecycle | Sync/update/delete | Blocked by plan; entitlement only verified |
| Hosted retrieval p95 | Product-specific | Insufficient samples |
| Domain accuracy | Product-specific | 12-case smoke: 12/12 memory vs 2/12 baseline; 100-case blinded suite pending |
| Support continuity | Memory beats empty-tenant baseline | 3/3 vs 0/3 on small synthetic suite |
| Verified lesson transfer | Memory improves related sandbox task | Memory passed; stateless failed on one hidden case |
| Immediate direct-fact visibility | Next agent can retrieve safely | Exact canaries passed first read in all paths; natural-query miss requires tuning |
| Prompt-injection resistance | No policy bypass | Governance 5/5 plus domain 2/2; larger adversarial suite pending |
| Retrieval policy | Domain precision/recall and latency gate | 120-search grid complete; winner 4/5 with zero false positives on synthetic corpus |
| Hierarchical context | Allowed scopes compose without policy bypass | Three-scope key passed; other tenant/revocation denied; action stayed false |
| Claim promotion | Stale/poisoned memory cannot become fresh truth | Four-channel fresh gate passed; memory-only cycle did not promote |
| Adaptive routing | Learned policy repairs after runtime failure | Calibration persisted; contract fallback passed; next process avoided failed route |
| Temporal recall | Natural dates retrieve correct event window | 10/10 exact, relative, future, and negative controls |
| Dependency risk | Exact-version evidence/test without autonomous change | Monid/Exa/Composio/SuperServe path passed; authorization stayed false |
| Governed correction | Only fresh/authorized evidence can revise truth | Poison quarantined; wrong hash/replay denied; exact versioned update passed |
| Multi-agent recovery | Fresh process reconstructs one valid chain | Signed three-stage restart, invalid-output denial, and retry dedup passed |
| Batch relationship readiness | Required account facts available before briefing | Batch accepted 3/3; Dynamic Dreaming timed out; normalized direct fallback passed |
| Incident certainty | No root-cause claim without evidence | Synthetic hypothesis gate passed; production cause stayed unknown and action unauthorized |
| Tool economics | Cheapest eligible route uses comparable dated cost | Exa/Monid ranked; unknown Composio cost stayed shadow; new process revalidated |
| Graph lineage/review | Current truth reconstructs correction history; review is exact-authorized | Nested `[1,2,3]` chain passed; ordinary review returned 409; instant run produced two one-parent candidates then zero on repeat; transition pending |
| Multi-model deliberation | Every valid vote cites evidence; dissent/staleness preserved | Three evidence-bound votes passed; fenced-JSON failure abstained; changed digest became stale |
| Adaptive tutoring | Only verified assessment changes signed mastery | Unsigned poison ignored; isolated 4/4 grade created v2; fresh process recovered it |
| Resumable due diligence | Budget/provider failures remain explicit and cannot promote partial work | Signed degraded resume passed; later sourced-environment run reached all six channels but insufficient evidence still did not promote |
| Change-risk advice | Passing rehearsal cannot override unhealthy current state | 5/5 sandbox plus unhealthy live counts correctly yielded HOLD; no deploy authority |
| Legal-hold retention | Exact policy/hold/approval, drift/replay denial, post-delete proof | Wrong authorization/drift/replay denied; one exact forget passed; external audit emitted |
| Subject transparency | Export actual inventory; exact erase is snapshot-bound and verifiable | Four documents/two memories plus history exported; drift/wrong auth/replay denied; exact document/memory absence passed |
| Contract drift | Upgrade advice is exact, current, and non-authoritative | 32-path snapshot and current reports yielded targeted HOLD; unchanged restart passed; changed digest stale |
| Long-horizon project state | Valid chain survives restart; completion requires verified artifact | Four-state signed chain, forged denial, sandbox 4/4, and fresh completion passed |
| Valid dissent | Minority evidence/falsifier survives proposal persistence | `HOLD/PILOT/HOLD` all valid; minority persisted; changed evidence stale |
| Batch migration | Retry/restart reconcile exactly; rollback retains pre-existing data | 10/10 import, same-ID replay, exact reconciliation, approval-bound rollback passed |
| Self-host durability | Restore and upgrade | Fresh run passed; durability/upgrade pending |
| SMFS maturity | Consistent read/search/profile | Read/search passed; profile/list quirks observed |

## Keep the integration replaceable

The `MemoryBackend` protocol in this repo is intentional. Product code should depend on
domain operations such as `recall_user`, `ingest_source`, `record_decision`, and
`forget_subject`, not on a framework wrapper scattered through model calls. That preserves
the ability to compare hosted, local, another provider, or a simpler implementation during
the free year without rewriting the agent.
