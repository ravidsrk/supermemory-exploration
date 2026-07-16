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

That conclusion is supported by the current [API model](memory-model.md), two hosted core
runs, a local-server run, an SMFS run, and a Memory Router control run. The detailed numbers
are in [Experiments](experiments.md).

## What is genuinely compelling

### 1. One read plane for personalization and knowledge

`/v4/profile` returns stable traits, recent context, optional bucketed attributes, and
query-specific search results. `/v4/search` can return distilled memories, raw chunks, or
both. A single agent can therefore retrieve “how this user works” and “what the source
said” without maintaining two unrelated retrieval stacks. This is more valuable than the
marketing label “memory”: it is a unified context contract.

**Observed:** direct stable and dynamic facts appeared in the expected profile sections,
and hybrid search returned both exact memories and the supporting document chunk.

### 2. Exact writes coexist with learned writes

Direct v4 creation makes a confirmed fact immediately searchable. Document and
conversation ingestion asynchronously extract candidate facts. That supports an important
separation:

- write confirmed decisions, permissions, and handoffs directly;
- ingest conversations and documents when extraction is the desired behavior;
- use `taskType=superrag` for sources that should remain citable knowledge rather than
  become user traits.

**Observed:** direct creation was available in about one second from the client; document
extraction took roughly 18–33 seconds in the two hosted runs.

### 3. Knowledge evolution is a first-class operation

A memory update creates a new version and retains its parent. Forget is a soft-delete
operation. The documented graph can also extend or derive facts and exposes a human-review
queue for low-confidence inferred memories. This is much closer to the actual needs of a
long-lived agent than append-only embeddings.

**Observed:** changing the synthetic launch date created version 2, linked it to version 1,
and normal search returned the current date while preserving the old fact as parent context.

### 4. Isolation is simple and testable

Container tags create deterministic namespaces. A negative-control search against a
different tag returned zero results. Container-scoped API keys can additionally enforce a
single tag at the credential layer. See the official
[container model](https://supermemory.ai/docs/concepts/container-tags) and
[scoped-key documentation](https://supermemory.ai/docs/authentication).

**Observed:** a scoped key could read and write its bound container, received `403` for both
operations against another container, and received `401` immediately after revocation.

## Where caution is required

### Memory Router is not yet the default recommendation

The Router is a transparent OpenAI-compatible proxy that promises compression, retrieval,
and fail-open forwarding. In this lab it successfully forwarded OpenRouter calls, stored a
raw searchable chunk, modified context, and kept another user isolated. It did **not**
recall the synthetic fact in a new conversation. Reusing the conversation ID returned the
previous acknowledgement instead of answering the new question. Sending full history
answered correctly, which only validates the model, not memory retrieval.

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

Two examples found in this pass:

- omitting v4 `searchMode` behaved as `memories`, not hybrid; the generated SDK says
  `memories`, while some overview language implies hybrid;
- the memory-update prose omitted the required `containerTag`; the hosted endpoint rejected
  the request without it and the generated SDK includes it.

Use explicit parameters even when defaults look convenient. Treat generated SDK types plus
a contract test as the effective API contract.

## Adoption recommendation

| Use case | Recommendation | Why |
|---|---|---|
| Per-user assistant profile | **Adopt with guardrails** | Strong profile/read model; keep consent and delete controls. |
| Project/research notebook | **Adopt** | Hybrid retrieval, citations, metadata, and `superrag` fit well. |
| Multi-agent handoff board | **Adopt for context, not locking** | Direct facts and aggregate recall work; use a DB/queue for coordination state. |
| Decision journal | **Adopt** | Exact writes and version history match the domain. |
| Customer-support copilot | **Pilot** | Valuable personalization; requires tenancy, PII, and deletion review. |
| Autonomous action authorization | **Do not use as authority** | Retrieved text is probabilistic and prompt-injectable. |
| Transparent Memory Router | **Prototype only** | Failed the lab's cross-session recall control. |
| Plan-gated connector product | **Verify entitlement first** | Crawler was blocked on this account. |
| Self-hosted production | **Pilot after upgrade/backup tests** | Core worked; current issue queue shows operational risk. |

## The non-negotiable architecture rule

Supermemory may tell an agent what it previously learned. It must not decide what the agent
is allowed to do. Money movement, deletion, outbound messages, deployment, access control,
and other consequential actions must be authorized from deterministic application state.
