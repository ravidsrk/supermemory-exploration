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
- six practical safety/combination systems for uploaded commitments, consent-bound intake,
  tool apprenticeship, contamination quarantine, least-privilege delegation, and governed
  all-provider readiness;
- five resilience/freshness systems for source-revision citation, additive profile-schema
  evolution, risk-aware continuity, checkpointed adaptive ingestion, and four-surface SLOs;
- five boundary systems for governed connector admission, exact maximum-cardinality rollback,
  concurrent four-surface recall, blinded 100-case evaluation, and stopped-state self-host
  recovery;
- systematic classification of all 255 auxiliary-provider subsets and live portfolio coverage
  of all 28 provider pairs;
- a causal sandbox transfer test where memory passed and the stateless candidate failed;
- a three-case support benchmark scoring 3/3 with memory and 0/3 without it;
- profile-versus-search read-after-write evidence and explicit polling barriers;
- source-pinned SDK, plugin, MCP, SMFS, and MemoryBench inspection;
- custom profile buckets, seven search-filter shapes, memory expiry/cancellation, inferred
  review endpoint/empty queue/ordinary-memory 409, three-version nested history, and queued
  container merge lifecycle;
- a correction-aware conversation-plus-direct-fact agent and preview-gated erasure agent;
- a 12-case matched domain smoke suite scoring 12/12 with memory versus 2/12 without;
- a blinded 100-case domain suite scoring 100/100 with memory versus 10/100 without, with zero
  errors, tenant leaks, or prompt-injection bypasses;
- a 600-document accepted/processed/searchable lifecycle and resumable six-by-100 exact
  deletion proof;
- same-directory restart and byte-identical clean-directory local restore, with production
  held for shutdown, worker, queued-ingestion, and upgrade blockers;
- a Router continuity matrix separating model history, direct memory pool, tenant isolation,
  and Router-generated cross-session persistence;
- practical wiki, production guardrails, evidence note, and benchmark plan.

Before month 1, rotate any credential that was pasted into an untrusted/public surface. Keep
all project keys out of git and use provider-specific least privilege where available.

## Month 1: turn observations into a domain baseline — August 2026

### Build

- Maintain and extend the completed blinded 100-question suite from
  [Benchmarks](benchmarks.md); the first final run scored 100/100 with memory versus 10/100
  without.
- Evolve the committed dataset schema with facts, updates, expected/forbidden evidence,
  tenant controls, and prompt-injection cases without changing rubrics after seeing answers.
- Retain repeatable result capture for quality, latency distribution, context tokens, and
  model usage; add reviewed cost accounting before production.
- Schedule exact profile/memories/hybrid/documents canaries in an isolated synthetic container;
  retain signed latency/miss/leak reports and test one injected outage monthly.
- Require chunk-digest revision binding for the cited research notebook and implement reviewed,
  drift-safe profile bucket evolution before cohort rollout.
- Expand the passing single-/multi-container and `429`/revocation scoped-key probes across the
  remaining documented endpoints and longer windows.
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

The governed onboarding state machine is ready and the current account boundary is proven:
connection creation returned `403` before OAuth, produced no connection/link/document, and
was classified as `plan-or-entitlement-blocked`. Resource selection, sync, and revocation
still require entitlement and a consenting OAuth user.

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

The v0.0.5 stopped-state drill now passes direct-memory restart, byte-identical backup, clean
restore, search/profile persistence, and exact deletion. Production remains a HOLD: shutdown
returned signal-derived `-5`, detached workers required reaping, a v3 document remained queued
for 180 seconds, and no release newer than v0.0.5 existed for an upgrade rehearsal.

### Gate

No self-hosted production decision without a successful restore to a clean machine and an
upgrade rehearsal from the deployed version.

## Month 5: scale, economics, and provider challenge — December 2026

### Benchmark

- Expand the passing one-question MemoryBench/OpenRouter wiring smoke to two public datasets;
  first diagnose its zero-result retrieval and keep exact post-run cleanup.
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
9. Run exact four-surface canaries and inspect processing backlog; hard-alert on any forbidden
   tenant marker, then compare latency/error budgets with the prior month.

## Scorecard

| Dimension | Target | Current first-pass status |
|---|---|---|
| Isolation | Zero negative-control leaks | Passed container, Router-user, and scoped-key read/write controls |
| Exact fact lifecycle | Create/update/forget works | Passed |
| Source retrieval | Correct chunk and citation | Passed synthetic text |
| Profile usefulness | Stable/dynamic are relevant | Passed synthetic facts and custom bucket classification |
| Cross-session Router | Recalls synthetic fact | Direct API pool passed; Router-generated new-conversation recall failed |
| Connector lifecycle | Sync/update/delete | Governed pre-OAuth intent/negative cleanup passed; hosted create returned entitlement `403`, so OAuth/resource/sync/revoke remain external-blocked |
| Hosted retrieval p95 | Product-specific | 100-case search p95 1.018 s plus bounded concurrent surface p95s recorded; still insufficient for a production SLA |
| Domain accuracy | Product-specific | Blinded synthetic suite: 100/100 memory vs 10/100 baseline; zero errors/leaks/bypasses |
| Support continuity | Memory beats empty-tenant baseline | 3/3 vs 0/3 on small synthetic suite |
| Verified lesson transfer | Memory improves related sandbox task | Memory passed; stateless failed on one hidden case |
| Immediate direct-fact visibility | Next agent can retrieve safely | Exact canaries passed first read in all paths; natural-query miss requires tuning |
| Prompt-injection resistance | No policy bypass | Governance 5/5, smoke domain 2/2, and blinded domain 5/5; broader real-source adversarial review pending |
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
| Uploaded commitment extraction | Every commitment has owner/date/exact source quote | Two commitments passed; wrong approval/replay denied; temporary URL not persisted |
| Consent-bound intake | No write outside subject/purpose/category/sensitivity/retention grant | Safe dynamic/document writes passed; four unsafe cases withheld |
| Memory quality | Critical contamination removed without model seeing raw sensitive content | Secret/injection quarantined; contradiction retained for review |
| Delegated least privilege | Cross-scope denied; revocation/rate window enforced | `403` read/write, `401` revoked, `[200,200,429]` plus `Retry-After` passed |
| Provider-combination coverage | All subsets classified; every provider pair exercised | 255 subsets classified; 28/28 live portfolio pairs; all-provider review passed |
| Source freshness | Current citations cannot survive a source replacement | V1 snapshot became stale; V2 exact quote/digest persisted once; poison/replay denied |
| Profile schema evolution | Existing/effective buckets survive reviewed additive change | Five suggestions validated; concurrent drift denied; initial/concurrent/new buckets retained |
| Recall continuity | Stale use is explicit/risk-bounded; high-risk fails closed | Signed restart cache, query-class/tamper denial, circuit skip, no-model high-risk failure, and recovery passed |
| Bulk backpressure/readiness | Rate response, resume, processing, and exact inventory are distinct | Injected 429 reduced 8→4; signed 9/24 resume reached 24/24 done/searchable |
| Memory SLO | Profile/memory/hybrid/document correctness and isolation stay visible | 12/12 small canary run, zero leaks; injected forbidden result produced signed alert |
| Maximum-cardinality lifecycle | Schema max/rejection, timeout ambiguity, exact rollback | Local 601/101 denial; hosted 600/600 done/searchable; six exact 100-ID deletes; restart-safe checkpoint and empty verification passed |
| Concurrent recall | Correctness and isolation at bounded parallelism | 20/20 sequential and 20/20 at eight workers; zero errors/leaks; not a sustained load test |
| Self-host durability | Restore and upgrade | Direct-memory backup/restart/clean restore/delete passed; production HOLD for signal-5 shutdown, orphan workers, queued ingestion, and unavailable newer-version upgrade |
| SMFS maturity | Consistent read/search/profile | Read/search passed; profile/list quirks observed |

## Keep the integration replaceable

The `MemoryBackend` protocol in this repo is intentional. Product code should depend on
domain operations such as `recall_user`, `ingest_source`, `record_decision`, and
`forget_subject`, not on a framework wrapper scattered through model calls. That preserves
the ability to compare hosted, local, another provider, or a simpler implementation during
the free year without rewriting the agent.
