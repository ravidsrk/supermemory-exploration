# Practical verdict

## Bottom line

Supermemory is best understood as a managed **context system**, not merely a vector
database and not a replacement for an application database. Its useful combination is:

- asynchronous document/conversation extraction into small facts;
- low-latency semantic recall of facts, document chunks, or both;
- a profile read that separates stable traits from recent context;
- versioned knowledge updates, relationships, and soft forgetting;
- strict container namespaces;
- connectors, framework wrappers, MCP, a filesystem interface, and a local binary.

The strongest production pattern today is to use the **explicit APIs**: keep canonical
state in the application database, send selected durable context to Supermemory, retrieve
bounded context before a model call, and treat generated memories as untrusted evidence.
This keeps authority, citations, isolation, and failure behavior under application control.

That conclusion is supported by the current [API model](memory-model.md), hosted core and
lifecycle runs, a 12-case matched domain benchmark, a local-server run, an SMFS run, and two
Memory Router control passes. The detailed numbers are in [Experiments](experiments.md).

## What is genuinely compelling

### 1. One read plane for personalization and knowledge

`/v4/profile` returns stable traits, recent context, optional bucketed attributes, and
query-specific search results. `/v4/search` can return distilled memories, raw chunks, or
both. A single agent can therefore retrieve “how this user works” and “what the source
said” without maintaining two unrelated retrieval stacks. This is more valuable than the
marketing label “memory”: it is a unified context contract.

**Observed:** direct stable and dynamic facts appeared in the expected profile sections,
and hybrid search returned both exact memories and the supporting document chunk.

### 2. Exact writes coexist with learned writes, but visibility is mode-dependent

Direct v4 creation bypasses extraction and makes a confirmed fact available to the profile
quickly in the observed runs. Search visibility can lag. Document and conversation ingestion
asynchronously extract candidate facts. That supports an important separation:

- write confirmed decisions, permissions, and handoffs directly;
- ingest conversations and documents when extraction is the desired behavior;
- use `taskType=superrag` for sources that should remain citable knowledge rather than
  become user traits.

**Observed:** direct facts became profile-visible on the first poll at roughly one second in
the support and debugging runs. The tool-selection decision was profile-visible while hybrid
search still returned nothing inside a separate ten-second window. Earlier small exact facts
were searchable quickly; therefore a write acknowledgement is not a universal search barrier.
Document extraction took roughly 18–33 seconds in the two hosted runs. Use the profile for
immediate direct-fact context or poll the retrieval path required by the next step.

### 3. Knowledge evolution is a first-class operation

A memory update creates a new version and retains its parent. Forget is a soft-delete
operation. The documented graph can also extend or derive facts and exposes a human-review
queue for low-confidence inferred memories. This is much closer to the actual needs of a
long-lived agent than append-only embeddings.

**Observed:** changing the synthetic launch date created version 2, linked it to version 1,
and normal search returned the current date while preserving the old fact as parent context.
The preference agent used the same pattern to replace a user preference without duplicate
current facts. Server expiry hid a temporary fact, cancellation preserved another as version
2, and an asynchronous container merge moved data while preserving target settings. A later
three-version run found current version 3 as the top-level entry and reconstructed versions
`[1, 2, 3]` from its nested `history`, resolving the earlier latest-only interpretation.

### 4. Isolation is simple and testable

Container tags create deterministic namespaces. A negative-control search against a
different tag returned zero results. Container-scoped API keys can additionally enforce one
or several allowed tags at the credential layer. See the official
[container model](https://supermemory.ai/docs/concepts/container-tags) and
[scoped-key documentation](https://supermemory.ai/docs/authentication).

**Observed:** a scoped key could read and write its bound container, received `403` for both
operations against another container, and received `401` immediately after revocation. A
later three-scope key read organization, project, and user context, denied another tenant,
and preserved deterministic organization-over-user policy precedence.

### 5. It supports durable agent policies, if outcomes can correct them

The adaptive router persisted a model calibration winner across processes, then discovered
that the winner failed a related exact-output task. A runtime contract triggered a fallback,
wrote the failure outcome, and caused a new process to avoid the failed route. The
corroboration council similarly persisted only claims that passed a fresh-source gate.

This is a strong general pattern for model routes, retrieval settings, tool choices, and
workflow recipes: memory can carry a learned policy forward, while deterministic checks and
new outcomes revise it. Never interpret durable policy memory as permanent correctness.

### 6. It is useful as an operational recovery and evidence plane

A signed planner/researcher/reviewer chain survived fresh processes, deduplicated an exact retry,
and ignored forged state. A governed curator applied a hash-bound correction once and preserved
the update's parent/root lineage. An incident agent retained a verified synthetic lesson while
still saying the production cause was unknown.

These are stronger patterns than generic chat recall: memory helps another process reconstruct
what was learned, which evidence supported it, and which policy was last successful. It still
cannot replace workflow locks, an approval ledger, incident logs, or canonical state.

### 7. It supports governed deliberation and long-running research

A three-model council bound each vote to exact evidence and falsifiers, retained failure and
dissent paths, and made its proposal stale when evidence changed. A budgeted due-diligence
campaign resumed from a signed checkpoint and exposed three provider authentication failures
without presenting partial research as complete. An adaptive tutor recovered signed mastery
but accepted only an independently verified assessment update.

These are high-leverage uses: memory preserves evidence manifests, progress, proposals, and
learned state across processes. The application must still own budget enforcement, source
diversity, validation, grading, action authority, and current-state checks.

## Where caution is required

### Memory Router is not yet the default recommendation

The Router is a transparent OpenAI-compatible proxy that promises compression, retrieval,
and fail-open forwarding. In this lab it successfully forwarded OpenRouter calls, stored a
raw searchable chunk, modified context, kept another user isolated, and continued delta-only
conversations 3/3. Direct API memory in the same user pool influenced Router answers both with
and without a conversation header. It did **not** recall the Router-generated synthetic token
in a new conversation. Sending full history answered correctly, which validates the model
history path rather than generated-memory persistence.

This is one account and one model, but it is enough to reject an assumption of transparent
correctness. Use the Router for prototypes only until a workload-specific continuation,
cross-session, latency, token, and outage suite passes. The official surface is described
in the [Router docs](https://supermemory.ai/docs/memory-router/overview).

### Connectors are plan- and provider-dependent

The API/docs expose Google Drive, Gmail, Notion, OneDrive, GitHub, Granola, S3, and a web
crawler. The no-OAuth web-crawler probe returned `403` because the account was not on the
required Scale plan. A free or promotional API grant should not be assumed to include
connectors. Build a connector proof before basing a product plan on it.

### Self-hosting works, but is not “just a tiny binary” operationally

A fresh disposable v0.0.5 server successfully ingested, extracted, searched, and profiled
synthetic facts using local embeddings and an OpenRouter-compatible model endpoint.
First boot needed a model download and approximately 15 seconds before the worker was ready;
the process reported about 1.7 GB baseline memory and 1 GB ingestion headroom. This is
perfectly viable for a developer workstation and materially heavier than a small utility.

Current open issues report upgrade migrations, API-key auth, large-document queue wedges,
snapshot memory pressure, spreadsheet extraction, and wrapper regressions. These reports
were not reproduced, but they justify backup-and-restore tests and pinned versions before
self-hosting production. See [Ecosystem](ecosystem.md#current-risk-signals).

### Defaults and docs can drift

Examples found across the passes:

- omitting v4 `searchMode` behaved as `memories`, not hybrid; the generated SDK says
  `memories`, while some overview language implies hybrid;
- the memory-update prose omitted the required `containerTag`; the hosted endpoint rejected
  the request without it and the generated SDK includes it.
- the inspected SuperServe OpenAPI described Python 3.12 in `superserve/base`, while live
  `python3` execution returned command-not-found; the explicit Python 3.11 template worked.
- the Supermemory API changelog documents multi-container scoped keys, while the current
  authentication page still describes a singular `containerTag`; the hosted multi-tag key
  worked and also returned a legacy singular field;
- the Context.dev Markdown endpoint currently requires a GET query, while the lab's older POST
  adapter returned `403`; the corrected contract passed live.

Use explicit parameters even when defaults look convenient. Treat generated SDK types plus
a contract test as the effective API contract.

### Lifecycle recovery is not one uniform contract

In the same hosted account, `include.forgottenMemories=true` recovered a time-expired memory
but did not recover a directly forgotten one. A metadata-filtered memory-list request also
returned zero while unfiltered listing returned records, even though v4 search filters passed
all seven tested shapes. Build user-facing deletion around preview, deterministic approval,
negative verification, and a canonical audit ledger; do not promise restoration based only on
an include flag.

### Batch processing is not a synchronous fact-readiness contract

The three-document batch endpoint accepted every item, but repeated small
`dreaming=dynamic` runs remained in background Dreaming beyond 60–90 seconds and did not expose
the exact relationship fact during an additional bounded check. Writing the already-confirmed,
normalized CRM facts directly made the required next read pass.

This does not establish general Dynamic Dreaming latency or failure. It establishes that an
accepted batch, a `done` document, and a required extracted-memory read are different barriers.
Use batch Dreaming for background grouping/enrichment; use an exact read barrier and direct
fallback for synchronous agent state.

The larger matched matrix strengthened this conclusion. Eight instant jobs completed and
produced two inferred-review candidates once but zero on repeat; all eight dynamic Dreaming
jobs remained pending in both bounded runs. Candidate generation and Dreaming completion are
operator/background signals, not scheduling primitives.

### Tool economics and incident certainty need explicit unknown states

One tool portfolio exposed comparable costs for Exa and Monid but not Composio. Treating the
missing number as unknown and shadow-only prevented a false cheapest-route decision. Likewise,
read-only Vercel state without logs could not support a production root cause even though an
isolated synthetic rehearsal supported a mitigation pattern. `UNKNOWN` is a correct agent
output, not an error to be filled with model confidence.

The sixth due-diligence run extended this rule to provider health. Exa, Monid, and Composio
returned 401 while Context.dev and public social channels still worked. The correct result was
`degraded-partial`. The seventh pass traced those 401s to older process-environment credentials;
after sourcing the intended ignored local environment, all six acquisition channels worked.
Even then, the separate evidence gate refused promotion when relevance/citation support was
insufficient. Credential health, provider health, and evidence quality are three different
states.

### Retention and review need an external control plane

The list API exposed useful nested version history, and inferred review rejected an ordinary
memory with 409. A later instant run exposed two one-parent candidates, followed by zero on a
matched repeat; no qualifying candidate was transitioned. History and the review queue are not
immutable signature or workflow ledgers. A legal-hold rehearsal succeeded only because exact snapshot,
plan, approval, replay, and audit state lived outside the model and governed memory.

Use Supermemory for correction UX, current inventory, exact forgetting, and verification.
Keep legal interpretation, connector/back-up coverage, approval, immutable audit, and access
control elsewhere.

### Portability requires provider inventory and reconciliation

A subject export found provider-created backing documents in addition to explicit source
writes. A complete transparency workflow therefore enumerates and paginates documents,
chunks, memories, and history, signs the inventory, binds exact erasure IDs, and verifies both
absence and retained controls. Application logs alone are insufficient.

The same principle made batch migration recoverable. Stable custom IDs and source hashes,
a separately signed checkpoint, target-side reconciliation, and exact-ID bulk rollback
survived simulated acknowledgement loss at ten records while retaining a pre-existing control.
This is a strong small-case pattern; file uploads and documented cardinality boundaries remain
open.

### Memory can recover project state and dissent, not authorize either

A four-version project chain recovered `planned → active → review → done`, but review and
completion were valid only after an independently verified artifact digest and exact external
authorization. A three-model council also preserved a valid minority `PILOT` against two
`HOLD` votes. Both artifacts became stale on digest change. These are valuable memory-native
decision records, not locks, schedulers, graders, or action permissions.

### Treat contract changes as test generators

The current 32-path OpenAPI plus reported wrapper regressions produced a targeted
`HOLD-FOR-CONTRACT-TESTS`. This is the right granularity: issue titles are reports rather than
reproduced failures, and a schema diff is evidence for exact upgrade tests rather than an
automatic deploy or permanent block.

### The small domain result is encouraging, not dispositive

The bounded 12-case smoke suite scored 12/12 with memory versus 2/12 without, at 659 ms search
p50 and 1.14 s p95 with about 327 estimated context tokens. Tenant leaks and prompt-injection
bypasses were zero. This establishes a useful regression harness, not production-scale quality:
the next gate remains the blinded 100-case suite at realistic corpus volume.

## Adoption recommendation

| Use case | Recommendation | Why |
|---|---|---|
| Per-user assistant profile | **Adopt with guardrails** | Strong profile/read model; keep consent and delete controls. |
| Correction-aware preference agent | **Adopt with explicit promotion** | Conversation archival alone did not yield the fact promptly; normalized versioned writes did. |
| Project/research notebook | **Adopt** | Hybrid retrieval, citations, metadata, and `superrag` fit well. |
| Multi-agent handoff board | **Adopt for signed recovery, not locking** | Signed restart recovery and retry dedup passed; use a DB/queue for coordination state. |
| Decision journal | **Adopt** | Exact writes and version history match the domain. |
| Governed memory curator | **Pilot with external approval ledger** | Poison/hash/replay controls and versioned correction passed; graph context is not an audit signature. |
| Customer-support copilot | **Pilot** | Valuable personalization; requires tenancy, PII, and deletion review. |
| Competitive-intelligence memory | **Pilot** | Five-provider live path worked; public-social claims need corroboration. |
| Corroboration-gated research | **Pilot with publisher tracking** | Fresh/official/conflict gate resisted poisoned memory; provider diversity alone is not source independence. |
| Hierarchical enterprise copilot | **Pilot** | Three-scope key and policy precedence passed; application still owns authorization. |
| Adaptive model router | **Pilot with runtime contracts** | Cross-process policy repair worked, but the calibration winner failed a related task. |
| Temporal agenda | **Pilot** | Natural-date matrix passed; canonical clock and event state remain outside memory. |
| Dependency-risk guardian | **Pilot as decision support** | Exact-version evidence and isolated test passed; CVE feeds are incomplete and human approval remains required. |
| Relationship/account brief | **Pilot with consent and readiness fallback** | Four fresh channels and cited brief passed; Dynamic Dreaming was not a synchronous barrier. |
| Incident hypothesis forensics | **Adopt as read-only decision support** | Safely separated live observations from rehearsal and retained unknown root cause. |
| Tool-economics portfolio | **Pilot with dated costs** | Cross-process route worked; unknown cost, retries, and quality need continued calibration. |
| Multi-model decision council | **Pilot as proposal support** | Three evidence-bound votes and stale-digest control passed; majority remains non-authoritative. |
| Assessment-verified tutor | **Pilot with a validated grader** | Signed mastery and isolated update passed; the synthetic task is not a learning-validity study. |
| Resumable due diligence | **Adopt the degraded-state pattern** | Signed resume and citations worked; partial provider failure was visible and could not promote. |
| Operational change-risk board | **Adopt read-only/HOLD-first** | Live health overrode a passing rehearsal; no deploy authority exists. |
| Legal-hold retention controller | **Prototype with legal review** | Exact drift/replay/absence controls passed; broader storage and jurisdiction remain outside this API test. |
| Memory transparency/DSAR | **Pilot as an engineering control** | Actual-inventory export and exact erasure passed; connector/cache/backup and legal coverage remain open. |
| Contract-drift sentinel | **Adopt as an upgrade test gate** | Exact snapshot/staleness passed; reports and model advice remain non-authoritative. |
| Project Memory OS | **Pilot as recovery/briefing state** | Signed chain and verified artifact passed; keep workflow coordination transactional. |
| Valid-dissent council | **Adopt the dissent-preservation invariant** | Minority evidence/falsifier survived restart; calibration and independence remain unproven. |
| Batch migration reconciler | **Pilot before large migration** | Idempotent replay, exact reconcile, and rollback passed at ten records; boundaries remain open. |
| Sandboxed coding/debug agent | **Pilot with strict sandbox policy** | Memory-backed transfer passed where stateless failed; template and egress must be explicit. |
| Release-memory copilot | **Adopt read-only first** | Snapshot/history fit well; mutations remain approval-gated. |
| Temporary incident context | **Pilot** | Expiry/cancel worked; keep canonical incident state and verify disappearance. |
| Workspace consolidation | **Adopt as admin workflow** | Queued merge completed and retained target settings; source/target authorization stays deterministic. |
| Semantic privacy erasure | **Pilot behind preview** | Candidate gate worked; audit-recovery behavior remains inconsistent. |
| Autonomous action authorization | **Do not use as authority** | Retrieved text is probabilistic and prompt-injectable. |
| Transparent Memory Router | **Prototype only** | Failed the lab's cross-session recall control. |
| Plan-gated connector product | **Verify entitlement first** | Crawler was blocked on this account. |
| Self-hosted production | **Pilot after upgrade/backup tests** | Core worked; current issue queue shows operational risk. |

## The non-negotiable architecture rule

Supermemory may tell an agent what it previously learned. It must not decide what the agent
is allowed to do. Money movement, deletion, outbound messages, deployment, access control,
and other consequential actions must be authorized from deterministic application state.
