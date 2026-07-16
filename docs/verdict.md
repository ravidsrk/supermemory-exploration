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
2, and an asynchronous container merge moved data while preserving target settings.

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
| Multi-agent handoff board | **Adopt for context, not locking** | Direct facts and aggregate recall work; use a DB/queue for coordination state. |
| Decision journal | **Adopt** | Exact writes and version history match the domain. |
| Customer-support copilot | **Pilot** | Valuable personalization; requires tenancy, PII, and deletion review. |
| Competitive-intelligence memory | **Pilot** | Five-provider live path worked; public-social claims need corroboration. |
| Corroboration-gated research | **Pilot with publisher tracking** | Fresh/official/conflict gate resisted poisoned memory; provider diversity alone is not source independence. |
| Hierarchical enterprise copilot | **Pilot** | Three-scope key and policy precedence passed; application still owns authorization. |
| Adaptive model router | **Pilot with runtime contracts** | Cross-process policy repair worked, but the calibration winner failed a related task. |
| Temporal agenda | **Pilot** | Natural-date matrix passed; canonical clock and event state remain outside memory. |
| Dependency-risk guardian | **Pilot as decision support** | Exact-version evidence and isolated test passed; CVE feeds are incomplete and human approval remains required. |
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
