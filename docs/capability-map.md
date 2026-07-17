# Capability map

This map covers the current product surface discovered through the official
[documentation index](https://supermemory.ai/docs/llms.txt), public repositories, generated
SDKs, and live probes. “Maturity” is a lab judgment, not a vendor status label.

## Core API

| Capability | Practical use | Evidence | Maturity judgment |
|---|---|---|---|
| Add text, URL, or file | Knowledge ingestion and extraction | [Add document](https://supermemory.ai/docs/api-reference/ingest/add-document); hosted text probe | Core |
| Batch/file upload | Bulk knowledge loading; current OpenAPI accepts 1–600 documents and files up to 50 MB | [Current OpenAPI](https://api.supermemory.ai/v3/openapi); hosted batch, Markdown multipart, and maximum-cardinality runs | Core; local 601 rejection and hosted 600/600 accepted, processed, reconciled, and searchable. One earlier 60-second acknowledgement timeout proves the need for stable IDs and inventory reconciliation; 50 MB/file-format boundaries remain pending. |
| Structured conversation upsert | Preserve roles and append a conversation by ID | [Conversation endpoint](https://supermemory.ai/docs/api-reference/ingest/ingest-or-update-conversation); hosted probe | Core |
| `customId` upsert | Stable application identity for a document | Hosted probe; same document ID returned | Core, extraction semantics need regression tests |
| `dreaming=dynamic` | Group related content before memory creation | [Adding memories](https://supermemory.ai/docs/add-memories); repeated hosted batch probe | Asynchronous enrichment: small batches remained `dreaming` beyond 60–90 s and lacked the exact extracted fact in the extra check; use a direct confirmed-fact readiness fallback |
| `dreaming=instant` | Extract each document independently; extra documented operation | Same source; hosted probe | Core |
| `taskType=superrag` | Index knowledge without generating personal memory facts | [SuperRAG](https://supermemory.ai/docs/concepts/super-rag) | Core |
| Direct v4 memory creation | Exact facts without extraction; up to 100 per call | [Direct creation](https://supermemory.ai/docs/api-reference/content-management/create-memories-directly); hosted probes | Core; profile can precede search visibility |
| Versioned memory update | Correct a fact while preserving history | [Update](https://supermemory.ai/docs/api-reference/content-management/update-a-memory-creates-new-version); hosted probe | Core |
| Forget one memory | Remove a fact from normal search | [Forget](https://supermemory.ai/docs/api-reference/content-management/forget-a-memory); hosted probe | Core |
| Agentic mass-forget | Natural-language deletion with dry-run | [Forget matching](https://supermemory.ai/docs/api-reference/content-management/forget-memories-matching-a-promptquery); hosted probe | Slow/variable; background workflow only |
| Memory expiry (`forgetAfter`) | Lease temporary context and cancel through versioned update | Current [OpenAPI](https://api.supermemory.ai/v3/openapi); hosted expiry/cancel probe | Core; explicit forget and expiry had different recovery behavior |
| Memory history/list | Inspect current administrative inventory and mutation lineage | [Current OpenAPI](https://api.supermemory.ai/v3/openapi); hosted unfiltered three-version correction probe | Top-level entries represent current truth; the observed latest v3 entry nested history `[1, 2, 3]` with valid parent/root continuity. This corrects the earlier latest-only interpretation; test pagination/export and do not treat it as a compliance signature. |
| Document lifecycle | List, get, chunks, update, delete, processing state | [Document operations](https://supermemory.ai/docs/document-operations); hosted probes | Core; the 24-record run observed exact inventory while 16 records were still processing, then 24/24 done |
| Exact document chunks/file URL | Export ordered source chunks or obtain a temporary original-file URL | [Current OpenAPI](https://api.supermemory.ai/v3/openapi); hosted meeting-file run | Ordered chunk citation and temporary HTTPS URL passed. Official changelog says URLs expire after 24 hours; never persist them in memory, prompts, traces, or logs. |
| Bulk exact document delete | Roll back a known import set without semantic selection | [Current OpenAPI](https://api.supermemory.ai/v3/openapi); hosted ten-ID and six-by-100 rollback runs | Core for migration recovery; local 101-ID rejection, signed restart after 200 deletions, six exact 100-ID batches, idempotent completed replay, empty inventory, and negative search passed. Do not expose container-wide selectors to a model. |
| Organization settings/bucket suggestion | Inspect processing configuration and propose profile organization | [Current OpenAPI](https://api.supermemory.ai/v3/openapi); hosted additive-schema run | Five suggestions passed current shape validation. One was reviewed/applied only after signed effective-schema capture and concurrent-drift rejection; never grant suggestions direct mutation authority. |

## Recall and profile

| Capability | Practical use | Evidence | Guidance |
|---|---|---|---|
| v3 document search | Source-oriented RAG with chunks, summaries, full docs | [Search](https://supermemory.ai/docs/search); hosted probe | Use when document grouping/citations matter. |
| v4 memory search | Low-token distilled fact recall | [v4 search](https://supermemory.ai/docs/api-reference/recall-search/search-memory-entries); hosted probe | Make `searchMode="memories"` explicit. |
| v4 hybrid search | Facts and raw chunks together | Same source; hosted probe | Best default for research/support questions. |
| v4 document mode | Raw source retrieval through v4 | Same source | Use when extraction would discard wording. |
| Metadata filters | AND/OR, scalar, string, numeric, array, negation | [Filtering](https://supermemory.ai/docs/concepts/filtering); seven-shape hosted matrix | Put tenant in container; use metadata for subsets. Dotted search keys worked despite doc ambiguity. |
| Reranking | Better result order for added latency | [Search](https://supermemory.ai/docs/search) | Enable selectively; benchmark quality gain. |
| Query rewriting | Broader query understanding for added latency | Same source | Use for difficult natural-language queries, not every turn. |
| Natural-language time windows | Retrieve past, present, and future facts using phrases such as `last week` or `in August 2026` | [June 25 API changelog](https://supermemory.ai/changelog/api/); 10-case hosted matrix | Passed with rewrite off/on on a three-event corpus; provide trusted date/timezone and keep canonical event state elsewhere. |
| Aggregate results | Compress multiple memories into query-specific context | Current SDK/changelog and HandoffBoard probe contract | Useful for multi-agent boards; verify citations are not lost. |
| User profile | Stable, dynamic, bucketed, and query-specific context | [Profiles](https://supermemory.ai/docs/concepts/user-profiles); hosted probe | Excellent session-start primitive. |
| Profile buckets | Built-in preferences plus custom org/container categories | [Buckets API](https://supermemory.ai/docs/api-reference/profiles/get-profile-buckets); custom-bucket and schema-evolution hosted probes | Custom buckets persisted and classified the corrected fact. Treat evolution as additive schema: preserve container buckets, detect effective-key collision/drift, and remember organization buckets cannot be removed by a container update. |
| Inferred-memory review | Approve, decline, or undo generated inferences | [Memory review](https://supermemory.ai/docs/memory-review); endpoint/queue/negative-control and larger matrix | Add exact external authorization for sensitive personalization. Matched eight-document instant runs produced two one-parent candidates and then zero; dynamic produced none and remained pending. Ordinary-memory review returned 409. Generated-candidate approve/decline/undo remains pending. |

## Organization, isolation, and customization

| Capability | Notes |
|---|---|
| Container tags | Strict namespace, current v4 singular field, 100 characters, pattern `^[a-zA-Z0-9_:-]+$`. A negative-control search returned zero. |
| Scoped keys | One- or multi-container key, expiry and rate-window controls, restricted endpoint set. Hosted single-scope and three-scope reads, cross-tenant denial, and immediate revocation were observed. A delegated-worker key returned `403` for cross-scope read/write, `401` after revocation, and `[200,200,429]` with `Retry-After` at a two-request limit. Current authentication prose still shows the singular form. Prefer one short-lived container per user-facing or sandboxed worker. |
| Per-container entity context | Steers extraction for a domain or tenant. Treat it as processing configuration, not an authorization policy. |
| Organization context/filter prompt | Shapes extraction and relevance for new content. Existing content is not retroactively rebuilt. |
| Chunk size/settings | Organization-level ingestion tuning. Changing embedding dimension in self-hosting requires a new data directory. |
| Container merge/delete | Hosted merge queued an ID, exposed data at `cleanup_pending`, completed, removed the source, and retained target data/settings. Delete is consequential; both require deterministic authorization. |
| Metadata | Arbitrary source annotations and filters. Do not put secrets in metadata. |

The hosted document-list response used the key `memories` for document records in this pass.
The client handles that observed wire shape, but applications should keep document and memory
domain types distinct and contract-test upgrades. Direct v4 memory writes also appeared as
backing/administrative documents, so subject exports and deletion inventories must enumerate
the provider rather than count only explicit source-document writes.

## Integration surfaces

| Surface | Best fit | Current assessment |
|---|---|---|
| TypeScript/Python SDKs | Typed direct API access | Generated clients are useful; pin and wrap them. |
| `@supermemory/tools` | Framework middleware and tool factories | Convenient; explicit client remains easier to audit. |
| Vercel AI SDK | TypeScript chat/agent apps | First-class and broadly documented. |
| OpenAI SDK/Agents | Function tools and middleware | Open issues report default/fail-open drift; contract-test version used. |
| LangChain/LangGraph | Existing graph/chain stacks | Thin integration; preserve explicit container derivation. |
| Mastra/Agno/CrewAI/VoltAgent | Agent-framework adoption | Productized wrappers; evaluate the wrapper, not only the API. |
| Microsoft Agent Framework | .NET/Python agents | Supported; a current issue reports Python dedup type problems. |
| Convex | Backend-integrated memory | Supported, not lab-tested. |
| Pipecat/Cartesia | Voice agents | Useful asynchronous memory path; current issue reports Python wrapper bugs. |
| n8n/Zapier/viaSocket | No/low-code automation | Good for ingest workflows, not a trust boundary. |
| MCP | Portable `memory`, `recall`, identity/profile context | Current implementation lives in the monorepo; old standalone repo is deprecated. |
| Coding plugins | Automatic project/user recall and periodic capture | Useful reference architectures; auto-capture and scope deserve review. |
| Memory Router | Drop-in OpenAI-compatible proxy | Delta/full-history and direct API pool controls passed; Router-generated cross-session recall failed. Keep prototype-only. |
| Memory Graph UI | Explore documents, memories, relationships | Visualization, not evidence of a particular storage algorithm. |

Official integration pages currently include Vercel AI SDK, Microsoft Agent Framework,
Agno, OpenAI Agents, CrewAI, Convex, LangChain, LangGraph, Mastra, VoltAgent, Cartesia,
Pipecat, OpenAI, n8n, Zapier, viaSocket, Claude Memory, and several coding plugins. See the
[documentation index](https://supermemory.ai/docs/llms.txt) for the current list.

## Connectors

| Connector | Sync model / useful role | Access signal |
|---|---|---|
| Google Drive | Files and Google-native exports; workspace knowledge | Documented |
| Gmail | Threads with incremental Pub/Sub/webhook sync | Scale+ documented |
| Notion | Pages, databases, blocks, webhooks | Documented |
| OneDrive | Office documents and scheduled sync | Documented |
| GitHub | Selected repository documentation resources | Scale+ documented |
| Granola | Meeting notes/transcripts | Pro+ documented |
| S3-compatible | Object-bucket knowledge loading | Scale+ documented |
| Web crawler | Scheduled crawl with robots handling | Scale+; hosted probe returned 403 |

Connector OAuth can show Supermemory branding or use custom credentials for supported
providers. Treat each connection as a privileged ingestion principal; constrain its
container and selected resources. The governed live attempt bound provider/container/limits/
metadata/redirect in a signed intent, denied wrong authorization before the API, then received
hosted `403` before OAuth and created no resource. Current resource-management docs are
GitHub-specific. OAuth, selection, sync, update, revoke, and ACL-change behavior remain
unobserved until this account receives entitlement and a user consents.

## Alternative runtimes

### Self-hosted server

The local server exposes the hosted-style API with encrypted local storage, local or remote
embeddings, and a bring-your-own extraction model. The local edition is single-tenant and
does not include managed connectors/MCP. A v0.0.5 stopped snapshot, same-directory restart,
byte-identical clean restore, search/profile recovery, and exact deletion passed for direct
memory state. Production remains a HOLD on this macOS setup: parent shutdown returned signal
`-5`, detached workers required explicit reaping, a v3 ingest remained queued for 180 seconds,
and no newer release existed for a real upgrade drill. See
[self-hosting](https://supermemory.ai/docs/self-hosting/overview).

### SMFS

SMFS maps a container to filesystem semantics. The mount uses NFSv3 on macOS or FUSE on
Linux; the Bash tool provides a virtual shell for serverless agents. `memory.md`/`user.md`
are memory paths by default, other files use SuperRAG, `profile.md` is virtual, and plain
`grep` can become semantic. The lab validated the Python Bash tool, including write/read,
list, semantic search, and cleanup. It also found alpha quirks: delayed profile extraction
and a zero-byte list entry despite readable content. See [SMFS](https://supermemory.ai/docs/smfs/overview).

### Consumer app and browser extension

The app, Nova agent, extension, and memory graph let an individual collect and query
personal context without building an application. They share concepts with the developer
platform but should be evaluated separately for export, deletion, capture scope, and privacy.

## What is not a capability

- Supermemory is not a transactional database, queue, lock service, scheduler, or policy engine.
- Semantic similarity is not permission or identity verification.
- A graph visualization does not guarantee that every answer is graph-reasoned.
- A high benchmark score does not establish production quality without latency and context-token cost.
- Fail-open generation means availability can survive while memory correctness silently degrades.
