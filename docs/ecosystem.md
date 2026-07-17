# Ecosystem, internals, and source notes

## What is open and what is inspectable

The public [supermemory monorepo](https://github.com/supermemoryai/supermemory) is MIT-licensed
and actively developed. The inspected snapshot contains documentation, consumer web/app
code, extension, current MCP implementation, memory-graph UI, framework tools, validation
schemas, and integrations. The current tree does not expose an obvious hosted API engine
implementation matching the older `apps/api` references found in some repository guidance.

The self-hosted engine is distributed as a platform-specific release binary. It is practical
to run and presents the API locally, but the hosted proprietary extraction models and managed
backend cannot be fully audited from the inspected source. Therefore:

- **open source repository** is true for the public product/tooling tree;
- **self-hostable local server** is true and was observed;
- **every production engine/model detail is open source** was not established.

This distinction matters for security review, reproducibility, and claims that a visible graph
UI proves a particular internal retrieval algorithm.

## Repository landscape on 2026-07-16

GitHub API counts are a point-in-time popularity/activity signal, not a quality score.

| Repository | Stars observed | Role |
|---|---:|---|
| [supermemory](https://github.com/supermemoryai/supermemory) | 28,401 | Main product and tooling monorepo |
| [claude-supermemory](https://github.com/supermemoryai/claude-supermemory) | 2,691 | Claude Code plugin |
| [supermemory-mcp](https://github.com/supermemoryai/supermemory-mcp) | 1,710 | Older standalone MCP; repository marks it deprecated |
| [opencode-supermemory](https://github.com/supermemoryai/opencode-supermemory) | 1,419 | OpenCode plugin |
| [openclaw-supermemory](https://github.com/supermemoryai/openclaw-supermemory) | 790 | OpenClaw plugin |
| [smfs](https://github.com/supermemoryai/smfs) | 466 | Filesystem mount and related tooling |
| [memorybench](https://github.com/supermemoryai/memorybench) | 293 | Provider/benchmark evaluation framework |
| [code-chunk](https://github.com/supermemoryai/code-chunk) | 200 | Code-aware chunking utility |
| [codex-supermemory](https://github.com/supermemoryai/codex-supermemory) | 43 | Codex hooks/plugin |
| [sdk-ts](https://github.com/supermemoryai/sdk-ts) | 18 | Generated TypeScript SDK |
| [pipecat-memory](https://github.com/supermemoryai/pipecat-memory) | 20 | Voice-agent memory integration |
| [infinite-chat](https://github.com/supermemoryai/infinite-chat) | 15 | Memory Router/infinite chat sample |
| [python-sdk](https://github.com/supermemoryai/python-sdk) | 0 | Generated Python SDK |

Other org repositories include examples, install-mcp, llm-bridge, preprint, Cursor integration,
Friend, and older/general-purpose projects. Pin the exact source snapshot for an audit; the
first pass commits are recorded in the [evidence note](../evidence/2026-07-16-field-lab.md).

## SDKs

The official TypeScript client is Stainless-generated. In the inspected commit it defaults to:

- one-minute per-request timeout;
- two retries;
- retries on connection failures, timeouts, HTTP 408, 409, 429, and 5xx;
- `warn` log level;
- `memories` as the v4 search-mode default.

Those defaults have operational consequences. A one-minute operation can take materially
longer after retries. A non-idempotent write should use a stable application identity. Debug
logging includes detailed request/response information; never enable it on sensitive data
without testing redaction.

The generated types were more reliable than one prose example in this pass: memory update
requires `containerTag`, and the hosted endpoint enforced it. See the pinned
[memory types](https://github.com/supermemoryai/sdk-ts/blob/3a191ae8bfb896f98f09ee1082c6180ce3438085/src/resources/memories.ts),
[search types](https://github.com/supermemoryai/sdk-ts/blob/3a191ae8bfb896f98f09ee1082c6180ce3438085/src/resources/search.ts), and
[client defaults](https://github.com/supermemoryai/sdk-ts/blob/3a191ae8bfb896f98f09ee1082c6180ce3438085/src/client.ts).

Practical recommendation: wrap the generated client behind a small domain interface, set
timeouts/retries explicitly, and keep black-box contract tests. The lab does this with a tiny
stdlib client so every request field under investigation is visible.

## Framework tools and middleware

The monorepo's framework packages make common choices automatically: when to retrieve, how
to inject context, when to save a conversation, how to deduplicate, and whether a memory
failure breaks the model call. That is convenient, but those choices are part of product
behavior and require tests.

The current docs include Vercel AI SDK, Microsoft Agent Framework, Agno, OpenAI Agents,
CrewAI, Convex, LangChain, LangGraph, Mastra, VoltAgent, Cartesia, Pipecat, OpenAI, n8n,
Zapier, viaSocket, and platform-specific plugins. The official Supermemory X account
[announced the Mastra plugin](https://x.com/supermemory/status/2020959115854610629) in
February 2026 as an auto-ingestion/low-token integration. Treat the announcement as product
positioning; benchmark the wrapper on the actual application.

## MCP

The current implementation is under `apps/mcp` in the main monorepo. Source inspection found:

- a `memory` tool to save or forget;
- `recall` for semantic retrieval;
- `whoAmI`;
- profile and project resources;
- a `context` prompt for profile injection;
- list/audit and interactive memory-graph surfaces.

It supports OAuth and API-key authentication. The older standalone
[supermemory-mcp](https://github.com/supermemoryai/supermemory-mcp) should not be used as the
source of truth merely because it has more historical stars.

MCP makes memory portable between clients, but the tool description actively encourages the
model to save informative facts. Products with sensitive data should narrow that instruction,
require explicit save intent, or put review in front of durable capture.

## Coding plugins as reference architectures

The inspected Codex plugin derives hashed user and project tags, uses entity-specific
extraction context, redacts `<private>...</private>` spans, limits injected profile/memories,
and exits cleanly when Supermemory fails. It supports session-start profile recall,
session-end flush, and configurable per-prompt recall/incremental capture. Source and README
defaults have evolved: fresh-install code currently resolves to session boundaries unless
enabled, while legacy/existing configurations may preserve three-turn capture and per-prompt
recall. This is exactly why plugin version/configuration must be recorded.

The plugin context uses `[SUPERMEMORY CONTEXT]` markers. Markers create a visual boundary but
are not, by themselves, a prompt-injection defense. Add an explicit “untrusted data, never
follow instructions” policy in the host agent.

The Claude, OpenCode, OpenClaw, Codex, and Hermes implementations are useful patterns for:

- separate personal and project scope;
- fail-open developer tooling;
- incremental versus end-session capture;
- entity context;
- privacy markup;
- custom containers.

They should not be copied blindly into a high-stakes agent where silent memory degradation
or automatic capture is unacceptable.

## Connectors

Connectors are managed ingestion workers, not a new read model. They sync external resources
into containers, after which normal document/memory/profile APIs apply. Current documented
providers include Drive, Gmail, Notion, OneDrive, GitHub, Granola, S3, and web crawling.

Important design questions for every connector:

1. Which external resources are selected?
2. Which deterministic container receives them?
3. How are updates, deletion, and revocation reflected?
4. Does source ACL change after indexing?
5. Which content can become profile memory versus RAG-only chunks?
6. Who sees the OAuth branding and consent text?
7. What plan and rate limits apply?

The current account's crawler call was rejected as Scale-only. Connector presence in docs
does not imply account entitlement.

## SMFS

The [SMFS repository](https://github.com/supermemoryai/smfs) is open and the docs describe two
related products:

- a real mount using NFSv3 on macOS or FUSE on Linux;
- TypeScript/Python virtual Bash tools for serverless runtimes.

The mount caches local reads and syncs bidirectionally on a documented 30-second default.
Specific memory paths generate extracted facts; other files use SuperRAG. A virtual
`profile.md` gives a digest, and semantic grep maps familiar filesystem grammar to retrieval.

The Bash tool supports a broad parser of built-ins, pipes, redirection, loops, tests, search,
and text utilities. It is not a host shell. The lab used Python package v0.0.2 and found it
functional but visibly alpha. Use it for agent ergonomics, not POSIX compatibility.

## Self-hosted server

The official installer downloads a release asset and verifies its checksum. Local state,
auth material, and model cache live under one data directory, making backup conceptually
simple. Extraction needs a provider model; embeddings default to a local English 768d model.

The local server is attractive when:

- data residency or offline operation is mandatory;
- workload scale is known and capacity can be owned;
- connector/MCP platform features are unnecessary;
- the team can run backup, upgrade, and model-quality evaluations.

Hosted is attractive when managed connectors, optimized proprietary extraction, and global
capacity matter. The local-versus-hosted choice also changes memory quality because the
extraction model changes, so API compatibility does not guarantee result equivalence.

## Memory Router

The Router prepends Supermemory to an OpenAI-compatible provider URL, takes provider and
Supermemory keys separately, and shares a memory pool by `user_id`. Official docs claim
context compression, automatic retrieval, asynchronous writes, provider-agnostic forwarding,
fail-open behavior, and significant token savings. Those claims are valuable hypotheses.

The field-lab recall control failed even though forwarding and raw chunk storage worked. Do
not rely on “drop-in” as a substitute for continuation tests. Also verify current pricing and
response diagnostic headers directly; product pages can lag implementation.

## Current risk signals

These are **open issue reports observed on 2026-07-16**, not reproduced facts. They identify
where a production proof should focus:

- [#1296](https://github.com/supermemoryai/supermemory/issues/1296): self-hosted macOS process allegedly wedges and resists termination.
- [#1293](https://github.com/supermemoryai/supermemory/issues/1293): self-hosted v0.0.5 upgrade profile-bucket migration.
- [#1291](https://github.com/supermemoryai/supermemory/issues/1291): document ingestion after v0.0.3 → v0.0.5 upgrade.
- [#1287](https://github.com/supermemoryai/supermemory/issues/1287): OpenAI middleware allegedly fails closed on API outage.
- [#1266](https://github.com/supermemoryai/supermemory/issues/1266): Python wrapper result-shape/dedup failures.
- [#1247](https://github.com/supermemoryai/supermemory/issues/1247): package drift between AI SDK integrations.
- [#1246](https://github.com/supermemoryai/supermemory/issues/1246): MCP list/graph scope inconsistency.
- [#1241](https://github.com/supermemoryai/supermemory/issues/1241): OpenAI middleware add default differs from docs.
- [#1203](https://github.com/supermemoryai/supermemory/issues/1203): self-hosted large-document queue wedge.
- [#1177](https://github.com/supermemoryai/supermemory/issues/1177): self-hosted snapshot memory pressure/data lifecycle.
- [#1152](https://github.com/supermemoryai/supermemory/issues/1152): self-hosted XLSX extraction.

The correct response is not to conclude the product is broken. It is to pin versions and turn
each relevant report into a release-gate test.

## Product trajectory and research culture

The changelog and repository show rapid expansion from basic v3 ingestion/search into v4
memory operations, profiles/buckets, inference review, scoped keys, self-hosting, SMFS,
Memory Router, coding plugins, and aggregate retrieval. Rapid surface growth creates leverage
and integration drift.

A particularly useful signal came from founder Dhravya Shah's March 2026
[benchmark post](https://x.com/DhravyaShah/status/2036243995500966260): a ~99% agentic
system was explicitly revealed as impractical due to roughly 70-second retrieval and high
context usage, motivating multi-dimensional MemScore reporting. That is a healthy warning
against optimizing this deployment around a headline accuracy number—even the vendor argues
quality alone is insufficient.

The 2026-07-17 recheck pinned the monorepo at
[`82c03a8`](https://github.com/supermemoryai/supermemory/tree/82c03a87ce1e89302b915e55739c9482209e0408).
Its refreshed README foregrounds the official
[research](https://supermemory.ai/research/) claims of 95% Recall@15 at roughly 720 context
tokens on 500 LongMemEval questions and lower SMFS token use on xAFS. Treat those as vendor
research until reproduced on the application corpus.

A fresh official-X read returned nine bounded records. Recent product-direction signals
included a [local voice agent](https://x.com/supermemory/status/2077838827302125582), a
[Tesla-assistant hackathon build](https://x.com/supermemory/status/2077488434026012774), and a
[personalized writing agent](https://x.com/supermemory/status/2076637279628730771). They make
voice, ambient/local assistants, device copilots, and style-personalized generation useful
prototype categories. They do not prove tenant isolation, consent, latency, or durable recall;
use the same canary, intake, and source-freshness controls as any other agent.

Review the [API changelog](https://supermemory.ai/changelog/api/) and
[docs changelog](https://supermemory.ai/docs/changelog/overview) monthly and before upgrades.
