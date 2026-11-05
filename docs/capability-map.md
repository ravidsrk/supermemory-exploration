# Capability map — Supermemory as of Nov 2026 (API v5)

This page has every capability the Supermemory primary sources document as of
**2026-11-05**: the 202-page [docs index](https://supermemory.ai/docs/llms.txt), the live
[v5 OpenAPI](https://api.supermemory.ai/openapi.json) (`5.0.0`, 22 paths / 33 operations),
the [pricing page](https://supermemory.ai/pricing), and the
[changelog](https://supermemory.ai/changelog) through 2026-11-02. The July 2026 (v3/v4) map
is kept unchanged as an archive below. Its claims are marked **as of July 2026 / superseded
Nov 2026**.

**How to read the "Verified?" column**

| Label | Meaning |
|---|---|
| **Spec** | Route, field, enum, or limit confirmed in the live v5 OpenAPI fetched 2026-11-05 |
| **Docs** | Stated in the official docs, pricing page, or changelog only |
| **Live ✗ 401** | Exercised by [`experiments/run_memory_layer_lab_2026_11.py`](../experiments/run_memory_layer_lab_2026_11.py), but blocked because the workspace key returned 401 ([evidence](evidence/experiments/2026-11-05-memory-layer-lab.md)) |
| **July live (legacy)** | The v3/v4 equivalent was observed live in July 2026. That is not proof of v5 behavior |
| **Not exercised** | Has side effects outside a sandbox (OAuth, org-wide settings, paging staff), so it is intentionally not probed |

Status values: **GA** (documented, current), **Legacy-only** (served under `/v3`/`/v4` with
no v5 route), **Removed in v5**, **Alpha/Beta** (labelled so by vendor), **Discontinued**.

**Coverage:** 96 capability rows across 14 areas. Every inventoried capability has a row
(100%). On v5 in Nov 2026, **0** are live-verified because the key was rejected.
47 are spec-verified, 40 were attempted live and blocked (401), 22 have a July
legacy live observation, and 29 rest on docs alone.

## 1. Namespaces (formerly container tags)

| # | Feature | Docs | Status | Agent use case | Verified? |
|---|---|---|---|---|---|
| 1 | Namespace auto-created on first write | [Namespaces](https://supermemory.ai/docs/concepts/container-tags) | GA | Zero-provisioning per-user / per-agent memory | Docs · Live ✗ 401 · July live (legacy) |
| 2 | Naming rules `^[a-zA-Z0-9_:-]+$`, ≤100 chars; colon hierarchies (`org:acme:user:1`) | [Namespaces](https://supermemory.ai/docs/concepts/container-tags#naming-rules) | GA | Deterministic IDs derived from your tenant/user IDs | Spec |
| 3 | Scope in URL `/ns/{namespace}/…`; **one namespace per request** (no `containerTags[]`) | [Namespaces](https://supermemory.ai/docs/concepts/container-tags#scope-lives-in-the-url) | GA | Multi-scope recall = N requests merged in your app | Spec |
| 4 | Dedicated vector index per namespace (strict, not filtered) isolation | [Namespaces](https://supermemory.ai/docs/concepts/container-tags#how-it-works) | GA | Hard tenant boundary; no cross-user leakage | Docs · July live (legacy, zero leaks in 100-case suite) |
| 5 | List namespaces with `documentCount`/`memoryCount` (`GET /namespaces`, alias `GET /ns`, `q` search) | [List namespaces](https://supermemory.ai/docs/v5/api-reference/namespaces/list-namespaces) | GA | Admin dashboards, tenant inventory | Spec · Live ✗ 401 |
| 6 | Get namespace settings `GET /ns/{ns}` | [Get namespace](https://supermemory.ai/docs/v5/api-reference/namespaces/get-namespace-settings) | GA | Read per-tenant extraction steering | Spec · Live ✗ 401 |
| 7 | Namespace `supportingContext` (≤1,500 chars; was `entityContext`) `PATCH /ns/{ns}` | [Customization](https://supermemory.ai/docs/concepts/customization#supporting-context) | GA | Tell the extractor *who* this memory is about and what matters | Spec · Live ✗ 401 |
| 8 | Delete namespace `DELETE /ns/{ns}`, permanent; shared docs retained; `sm_project_default` undeletable | [Security → erasure](https://supermemory.ai/docs/overview/security) | GA | Right-to-erasure per user | Spec · Live ✗ 401 |
| 9 | Move namespace `DELETE /ns/{src}?moveTo=dst` (queued, `operationId`; replaces merge). **`moveTo` must be a query param** | [Namespaces](https://supermemory.ai/docs/concepts/container-tags#managing-namespaces) | GA | Consolidate an anonymous session into a signed-in user | Spec · Live ✗ 401 |
| 10 | Up to 1M documents / 10M memories per namespace | [Rules](https://supermemory.ai/docs/concepts/rules) | GA | Sizing: one namespace per user is not a scale risk | Docs |

## 2. Ingestion (documents in)

| # | Feature | Docs | Status | Agent use case | Verified? |
|---|---|---|---|---|---|
| 11 | Add text/conversation `POST /ns/{ns}/document` | [Add context](https://supermemory.ai/docs/ingestion/add-memories) | GA | Save a chat turn or note | Spec · Live ✗ 401 · July live (legacy) |
| 12 | Stable `id` (≤255; was `customId`). Re-POST appends/diffs | [Add context → updating](https://supermemory.ai/docs/ingestion/add-memories#updating-content) | GA | One document per session, so diff billing only charges new turns | Spec · Live ✗ 401 · July live (legacy) |
| 13 | URL ingest (fetched ≤10 MB), web pages, YouTube | [Content types](https://supermemory.ai/docs/concepts/content-types) | GA | Research agent saves sources by link | Docs · Live ✗ 401 |
| 14 | File upload `POST /ns/{ns}/document/file` (multipart, `metadata` as JSON string, ≤50 MB, `fileType`/`mimeType`) | [Upload file](https://supermemory.ai/docs/v5/api-reference/ingest/upload-file) | GA | Users drop PDFs/images into an agent | Spec · Live ✗ 401 · July live (legacy) |
| 15 | Replace document with file `POST /ns/{ns}/document/file/{id}` | [Replace with file](https://supermemory.ai/docs/v5/api-reference/ingest/replace-document-with-file) | GA | New version of a contract/spec | Spec |
| 16 | Partially update file document `PATCH /ns/{ns}/document/file/{id}` | [Partial file update](https://supermemory.ai/docs/v5/api-reference/ingest/partially-update-document-file) | GA | Fix metadata on an uploaded file | Spec |
| 17 | Batch add 1–600 documents `POST /ns/{ns}/document/batch` | [Backfill](https://supermemory.ai/docs/ingestion/batch-ingest-historical-data) | GA | Historical import, corpus load | Spec · Live ✗ 401 · July live (legacy 600/600) |
| 18 | `date` (was `documentDate`) for historical backfill | [Backfill](https://supermemory.ai/docs/ingestion/batch-ingest-historical-data) | GA | Correct temporal ordering of old chats/emails | Spec |
| 19 | `dreaming: "dynamic"` (default): batches related docs; memories can lag "done" by minutes | [How it works → dreaming](https://supermemory.ai/docs/concepts/how-it-works#dreaming-how-memories-enter-the-graph) | GA | Production sessions and connectors | Spec · Live ✗ 401 · July live (legacy; lag 60–90 s+) |
| 20 | `dreaming: "instant"`: per-document, +1 operation | [Processing modes](https://supermemory.ai/docs/ingestion/add-memories#processing-modes) | GA | "Remember this now": the v5 replacement for direct memory writes | Spec · Live ✗ 401 · July live (legacy) |
| 21 | `taskType: "superrag"`: chunk/embed only, no memories/profile, 5× cheaper | [SuperRAG](https://supermemory.ai/docs/concepts/super-rag) | GA | Reference corpora that must not shape the user profile | Spec · Live ✗ 401 |
| 22 | Filtered writes `group` (was `filterByMetadata`) | [Filtered writes](https://supermemory.ai/docs/ingestion/add-memories#filtered-writes) | GA | Keep team A's facts from building on team B's in a shared namespace | Spec |
| 23 | Per-request `supportingContext` on add | [Add context → parameters](https://supermemory.ai/docs/ingestion/add-memories#parameters) | GA | Inline steering without a separate call | Spec |
| 24 | Content types: text/MD/HTML, PDF, DOC/DOCX, Google Docs/Sheets/Slides, images (OCR), audio/video (transcription), code (AST-aware chunking), JSON/CSV. Text ≤1 MB | [Content types](https://supermemory.ai/docs/concepts/content-types) | GA | Multimodal agent inputs | Docs |
| 25 | Advanced PDF extraction (figure/diagram descriptions), auto-selected on Scale+ | [Content types → advanced](https://supermemory.ai/docs/concepts/content-types#advanced-document-extraction) | GA (Scale+) | Technical/financial PDFs | Docs |
| 26 | Pipeline `system.status` (queued→extracting→chunking→embedding→indexing→done/failed) plus separate `system.dreamingStatus` | [Document operations](https://supermemory.ai/docs/ingestion/document-operations#processing-status) | GA | Agents wait for `dreamingStatus=done` before reading memories | Docs · Live ✗ 401 |

## 3. Documents, chunks, and lists

| # | Feature | Docs | Status | Agent use case | Verified? |
|---|---|---|---|---|---|
| 27 | Get document `GET /ns/{ns}/document/{id}?include=chunks,memories` (Supermemory or your `id`) | [Get document](https://supermemory.ai/docs/v5/api-reference/content-management/get-document) | GA | Show what was learned from one source | Spec · Live ✗ 401 |
| 28 | Update document `PATCH /ns/{ns}/document/{id}`: content replaces and reprocesses; metadata-only merges, no reindex | [Update document](https://supermemory.ai/docs/ingestion/document-operations#update-document) | GA | The v5 way to *correct* a fact | Spec · Live ✗ 401 |
| 29 | Delete documents `DELETE /ns/{ns}/document` (1–100 ids; partial `errors`; processing docs refuse) | [Delete](https://supermemory.ai/docs/v5/api-reference/content-management/delete-documents) | GA | Remove a source and its derived memories | Spec · Live ✗ 401 · July live (legacy) |
| 30 | Unified list `POST /ns/{ns}/list/{documents\|chunks\|memories}` with filter, sort, order | [List resources](https://supermemory.ai/docs/v5/api-reference/content-management/list-resources) | GA | Memory transparency UI, audits | Spec · Live ✗ 401 |
| 31 | Cursor pagination `pagination.nextCursor`/`hasMore` (2026-11-02; TS SDK ≥5.1.1) | [Changelog](https://supermemory.ai/changelog) | GA | Export / reconcile a whole tenant | Spec · Live ✗ 401 |
| 32 | `include.content` (extracted text) on document lists (2026-10-21); `include.forgotten`, `include.memoryCount` | [Document operations](https://supermemory.ai/docs/ingestion/document-operations#include-extracted-content) | GA | One-call export | Spec · Live ✗ 401 |
| 33 | Memory counts per document `POST /ns/{ns}/list/documents/memory-counts` (1–100) | [OpenAPI](https://api.supermemory.ai/openapi.json) | GA | Spot sources that produced no memories | Spec · Live ✗ 401 |

## 4. Memories and the graph

| # | Feature | Docs | Status | Agent use case | Verified? |
|---|---|---|---|---|---|
| 34 | Automatic memory extraction (atomic facts); types: facts, preferences (strengthen), episodes (decay) | [Graph memory](https://supermemory.ai/docs/concepts/graph-memory#memory-types) | GA | No schema to maintain | Docs · July live (legacy) |
| 35 | Relationships `updates` / `extends` / `derives`; `isLatest` keeps recall on the current truth | [Graph memory → relationships](https://supermemory.ai/docs/concepts/graph-memory#memory-relationships) | GA | "Alex moved from Google to Stripe" resolves itself | Docs · Live ✗ 401 |
| 36 | Inferred memories flagged `isInference: true` | [Search response](https://supermemory.ai/docs/recall/search) | GA | Separate "user said" from "model guessed" in prompts | Docs · Live ✗ 401 |
| 37 | Inferred-memory review queue + approve/decline/undo (`/v3/container-tags/{ns}/inferred[/{id}/review]`) | [Memory review](https://supermemory.ai/docs/recall/memory-review) | GA (legacy path family) | Human-in-the-loop memory curation | Docs · Live ✗ 401 (list only; decisions not exercised) |
| 38 | Get memory `GET /ns/{ns}/memories/{id}?include=related,documents&relatedLimit=` | [Get memory](https://supermemory.ai/docs/v5/api-reference/content-management/get-memory) | GA | Explain *why* the agent believes something | Spec · Live ✗ 401 |
| 39 | Automatic forgetting: time-based expiry, contradiction, noise filtering | [Graph memory → forgetting](https://supermemory.ai/docs/concepts/graph-memory#automatic-forgetting) | GA | "Exam tomorrow" does not haunt next month | Docs |
| 40 | Forget by ID `DELETE /ns/{ns}/memories` (1–500; soft; per-ID `errors`) | [Memory operations](https://supermemory.ai/docs/recall/memory-operations#forget-memories) | GA | "Forget that" tool | Spec · Live ✗ 401 · July live (legacy) |
| 41 | Semantic forget `DELETE /ns/{ns}/memories/semantic` (`dryRun` required, ≤100 per request, +1 op per round, ≤5) | [Forget matching](https://supermemory.ai/docs/recall/memory-operations#forget-matching) | GA | "Forget everything about Project Titan", with preview then exact-ID apply | Spec · Live ✗ 401 · July live (legacy) |
| 42 | Direct memory create (`POST /v4/memories`) | [Migration](https://supermemory.ai/docs/migration/api-v5) | **Removed in v5** (legacy-only) | Use `add` + `dreaming:"instant"` | July live (legacy) |
| 43 | Versioned memory update (`PATCH /v4/memories`) | [Migration](https://supermemory.ai/docs/migration/api-v5) | **Removed in v5** (legacy-only) | Use document `PATCH`; keep lineage in your DB | July live (legacy) |
| 44 | Conversation upsert (`POST /v4/conversations`) | [Migration](https://supermemory.ai/docs/migration/api-v5) | **Removed in v5** (legacy-only) | Use `add` with a stable session `id` | July live (legacy) |

## 5. Search / recall

| # | Feature | Docs | Status | Agent use case | Verified? |
|---|---|---|---|---|---|
| 45 | `POST /ns/{ns}/search`, default `searchMode: "hybrid"` (memories + chunks; branch on `memory` vs `chunk`) | [Search](https://supermemory.ai/docs/recall/search) | GA | Per-turn context enrichment | Spec · Live ✗ 401 |
| 46 | `searchMode: "memories"` | [Search modes](https://supermemory.ai/docs/recall/search#search-modes) | GA | Personal facts only | Spec · Live ✗ 401 · July live (legacy default) |
| 47 | `searchMode: "chunks"` (was `documents`) | [Search modes](https://supermemory.ai/docs/recall/search#search-modes) | GA | Pure RAG grounding with citations | Spec · Live ✗ 401 |
| 48 | `threshold` 0–1, default **0.3** (v4: 0.6) | [Search → threshold](https://supermemory.ai/docs/recall/search#threshold) | GA | Precision dial; chatbot example uses 0.6 | Spec · Live ✗ 401 |
| 49 | `limit` 1–100, default 10 | [Search](https://supermemory.ai/docs/recall/search#parameters) | GA | Token budget | Spec |
| 50 | `rerank`: `none` (default) / `order` (~+100 ms) / `aggregate`; +1 op when it runs | [Search → reranking](https://supermemory.ai/docs/recall/search#reranking) | GA | Hard queries in research agents | Spec |
| 51 | `rewriteQuery` (multi-rewrite + merge; +1 op) | [Search](https://supermemory.ai/docs/recall/search#parameters) | GA | Vague user questions | Spec |
| 52 | `include.documents` / `include.related` (parents/children/siblings) / `include.forgotten` | [Search → attachments](https://supermemory.ai/docs/recall/search#attachments) | GA | Graph traversal in one call; audit forgotten facts | Spec · Live ✗ 401 |
| 53 | Date mentions **boost** instead of filter; open-ended since/after/before/until (2026-10-15) | [Changelog](https://supermemory.ai/changelog/api/) | GA (behavior change) | Temporal questions no longer return empty | Docs |
| 54 | Typed metadata `filter`: `eq/neq`, `gt/gte/lt/lte`, `contains/notContains` (+`caseSensitive`), `arrayContains/arrayNotContains`, `and`/`or` ≤5 levels, ≤200 operands | [Filtering](https://supermemory.ai/docs/concepts/filtering) | GA | Soft scoping inside a tenant (team, source, status) | Spec (shape) · Live ✗ 401 |
| 55 | Metadata values: string/number/boolean/string[]; keys `[a-zA-Z0-9_.-]`, literal dots | [Filtering → key rules](https://supermemory.ai/docs/concepts/filtering#metadata-key-rules) | GA | Design metadata once | Docs |

## 6. Profiles

| # | Feature | Docs | Status | Agent use case | Verified? |
|---|---|---|---|---|---|
| 56 | `POST /ns/{ns}/profile` → `static` + `dynamic` + `buckets` (no query in v5; entries are `{id, memory}`) | [Profile API](https://supermemory.ai/docs/recall/user-profiles) | GA | Always-on system-prompt context, 1 call | Spec · Live ✗ 401 · July live (legacy) |
| 57 | Profile `filter` (same expression as search) | [Filtering profiles](https://supermemory.ai/docs/recall/user-profiles#filtering-profiles) | GA | Support agent sees only ticket-derived traits | Spec |
| 58 | Profile as Markdown (`Accept: text/markdown`) | [OpenAPI](https://api.supermemory.ai/openapi.json) | GA | Paste straight into a system prompt | Spec |
| 59 | Profile buckets: built-in `preferences`, org buckets (console), namespace buckets `GET/PUT/DELETE /ns/{ns}/profile/buckets` (≤50, add-only, desc ≤2,000) | [Buckets](https://supermemory.ai/docs/user-profiles/buckets) | GA | Topic-structured profile (work, goals, health…) | Spec · Live ✗ 401 |
| 60 | Bucket aggregation (`aggregated_*` synthesized entries) | [Buckets](https://supermemory.ai/docs/user-profiles/buckets#reading-buckets) | GA | Dense long-lived profiles | Docs |
| 61 | Profile not metered as a search query (v5) | [Billing](https://supermemory.ai/docs/overview/billing#search-and-profile) | GA | Call it every session; still cache short-TTL | Docs |

## 7. Organization and customization

| # | Feature | Docs | Status | Agent use case | Verified? |
|---|---|---|---|---|---|
| 62 | `GET/PATCH /organization` `organizationalContext` (was `filterPrompt`), plus namespace count | [Customization](https://supermemory.ai/docs/concepts/customization#organizational-context) | GA | Domain steering for all tenants (legal, support…) | Spec · Live ✗ 401 (GET only) |
| 63 | Chunk size (`PATCH /v3/settings`) | [Customization → chunk size](https://supermemory.ai/docs/concepts/customization#chunk-size) | Legacy-only | Citation-heavy corpora (256–512) | Docs |
| 64 | Connector branding / custom OAuth apps (Drive, Notion, OneDrive) | [Customization → branding](https://supermemory.ai/docs/concepts/customization#connector-branding) | Legacy-only settings | White-label "Log in to YourApp" | Docs |
| 65 | Removed: `settings.reset`, `suggestBuckets`, `documents.fileUrl`, `shouldLLMFilter`/categories | [Migration → settings](https://supermemory.ai/docs/migration/api-v5-settings) | **Removed in v5** | n/a | Docs |

## 8. Connectors

| # | Feature | Docs | Status | Agent use case | Verified? |
|---|---|---|---|---|---|
| 66 | Connector CRUD + sync: `POST/GET /ns/{ns}/connectors`, `GET/PATCH/DELETE …/{id}` (`deleteDocuments`), `POST …/{id}/sync` (409 if running), `GET /connectors` | [Connectors](https://supermemory.ai/docs/connectors/overview) | GA | Enterprise context agents fed from SaaS | Spec · Live ✗ 401 (list only) |
| 67 | Providers: Notion, Google Drive (incl. Slides), Gmail, OneDrive (folder picks), GitHub, S3, Web Crawler (weekly recrawl), Granola | [Connectors](https://supermemory.ai/docs/connectors/overview#supported-connectors) | GA, plan-gated: Pro (Drive/OneDrive/Notion/Granola), Max (Gmail), Scale (GitHub/S3/Web Crawler) | Pick by plan | Spec (enum) · Docs |
| 68 | Selection (`repos/labels/files/folders` ≤500), `documentLimit` ≤10,000, `include=syncs,picker` | [Managing resources](https://supermemory.ai/docs/connectors/managing-resources) | GA | Least-data ingestion | Spec |

## 9. Auth, limits, billing, ops

| # | Feature | Docs | Status | Agent use case | Verified? |
|---|---|---|---|---|---|
| 69 | Org API keys, `Authorization: Bearer sm_…` | [API keys](https://supermemory.ai/docs/authentication) | GA | Server-side agents | Live ✗ 401 |
| 70 | Scoped keys `POST /auth/scoped-key` (`containerTag` or `containerTags[]`, `expiresInDays` 1–365, `rateLimitMax` tiers 500…10,000), revoke `DELETE /auth/scoped-key/{id}` | [Scoped keys](https://supermemory.ai/docs/authentication#scoped-api-keys) | GA | Hand a per-user/per-agent key to an untrusted runtime | Docs · Not exercised · July live (legacy `/v3/auth/scoped-key`) |
| 71 | Member restrictions (per-namespace read/write), Scale+ | [Namespaces → access](https://supermemory.ai/docs/concepts/container-tags#access-control) | GA (Scale+) | Least-privilege humans | Docs |
| 72 | Rate limit default 500 req/min per key, `429` + `Retry-After` + `RATE_LIMITED` | [Billing → HTTP](https://supermemory.ai/docs/overview/billing#http-behavior-when-gated) | GA | Back-off in agent loops | Docs |
| 73 | Error contract: 400 (unknown params), 402 credits, 403 plan/feature or namespace, 409 merge/sync in progress | [Add context → errors](https://supermemory.ai/docs/ingestion/add-memories) | GA | Fail-open handling | Docs · Live ✗ 401 (401 confirmed) |
| 74 | Billing APIs `GET /v3/auth/billing`, `/usage`, `/usage-events`, `/invoices`, auto top-ups (admin/owner) | [Billing → programmatic](https://supermemory.ai/docs/overview/billing#programmatic-access) | GA (legacy path) | FinOps per agent | Docs · Not exercised |
| 75 | Analytics `GET /v3/analytics/usage\|errors\|logs` | [Analytics](https://supermemory.ai/docs/overview/analytics) | GA (legacy path) | Ops dashboards, error budgets | Docs |
| 76 | `POST /feedback` (bug/feature/docs; 3/day/org) | [Feedback](https://supermemory.ai/docs/v5/api-reference/feedback/send-feedback) | GA | Agent-filed vendor bug reports | Spec · Not exercised |
| 77 | Pricing (live page): **Free** $0 ($5 credits), **Pro** $19 ($20), **Max** $100 ($130), **Scale** $399 ($600), **Enterprise** custom. Rate card: memory text $5/M SM tokens, rich $10/M; SuperRAG $1/M, $2/M; search $5/M queries; operations $100/M | [Pricing](https://supermemory.ai/pricing) · [Billing](https://supermemory.ai/docs/overview/billing) | GA | Cost model in [memory-layer guide](memory-layer-for-agents-2026-11.md#10-cost-model) | Docs |
| 78 | Diff billing on stable `id` (unchanged content free) | [Billing → diff](https://supermemory.ai/docs/overview/billing#reusing-unchanged-content-diff-billing) | GA, all plans | Long sessions cost only the delta | Docs |
| 79 | Security: SOC 2 Type II, GDPR, HIPAA BAA (Scale/Enterprise), AES-256-class at rest | [Security](https://supermemory.ai/docs/overview/security) | GA | Regulated-domain agents | Docs |

## 10. SDKs, framework integrations, and tooling

| # | Feature | Docs | Status | Agent use case | Verified? |
|---|---|---|---|---|---|
| 80 | TypeScript SDK `supermemory` ≥5 (v5 only; positional `namespace`; retries 408/429/5xx; typed errors; 5.1 cursor) | [SDK](https://supermemory.ai/docs/integrations/supermemory-sdk) | GA | App code | Docs |
| 81 | Python SDK `supermemory` ≥5 (Python 3.10+; `dreaming_status` missing in 5.0.0, so use raw HTTP) | [SDK](https://supermemory.ai/docs/integrations/supermemory-sdk) | GA | App code | Docs |
| 82 | `@supermemory/tools` 3.0: Vercel AI SDK `withSupermemory` middleware (profile injection, `id` per conversation) + memory tools (`searchMemories`, `addMemory`, `getProfile`, `memoryForget`, `documentList/Add/Delete`); `@supermemory/ai-sdk` retired | [AI SDK](https://supermemory.ai/docs/integrations/ai-sdk) · [Tools 3.0](https://supermemory.ai/docs/migration/tools-v3-upgrade) | GA | Drop-in memory for TS agents | Docs |
| 83 | Framework guides: OpenAI SDK, OpenAI Agents SDK, LangChain, LangGraph, Mastra, VoltAgent, CrewAI, Agno, Microsoft Agent Framework, Convex, Eve | [Integrations](https://supermemory.ai/docs/integrations/openai) | GA | Use your existing agent framework | Docs · July live (contract matrix, legacy) |
| 84 | Voice: Pipecat, LiveKit, Cartesia | [Pipecat](https://supermemory.ai/docs/integrations/pipecat) | GA | Voice agents that remember callers | Docs |
| 85 | No-code: n8n, Zapier, viaSocket | [n8n](https://supermemory.ai/docs/integrations/n8n) | GA | Ops automations writing memory | Docs |
| 86 | Claude native memory tool backend (`/memories/*` paths → documents, `metadata.source="claude-memory"`) | [Claude memory tool](https://supermemory.ai/docs/integrations/claude-memory) | GA (needs Anthropic `context-management` beta) | Claude decides what to remember | Docs |
| 87 | Memory Graph React component (`@supermemory/memory-graph`) | [Memory graph](https://supermemory.ai/docs/integrations/memory-graph) | GA | User-facing "what I know about you" | Docs |
| 88 | CLI `npx supermemory`: `setup`, `login` (OAuth), `plugin`, `add/search/profile --namespace`, `namespaces`, `whoami`, `billing`, `local`, `migrate`, `help --json` | [Agents & MCP](https://supermemory.ai/docs/agents-and-mcp) | GA | Agent-driven setup and smoke tests | Docs |
| 89 | Agent skill (`npx skills add … --skill supermemory`) + Docs MCP `https://supermemory.ai/docs/mcp` | [Agents & MCP](https://supermemory.ai/docs/agents-and-mcp) | GA | Coding agents integrate correctly | Docs · Docs MCP reachable (200) |

## 11. Supermemory MCP and coding-agent plugins

| # | Feature | Docs | Status | Agent use case | Verified? |
|---|---|---|---|---|---|
| 90 | Hosted MCP `https://mcp.supermemory.ai/mcp` (OAuth; API key also accepted since 2026-08-21), "spaces" = namespaces | [MCP](https://supermemory.ai/docs/supermemory-mcp/mcp) | GA | One memory shared across Claude, ChatGPT, Cursor… | Docs · endpoint reachable (401 unauthenticated) |
| 91 | MCP tools: `search_memory`, `get_profile`, `add_memory`, `forget_memory`, `list_documents`, `get_document`, `list_memories`, `list_spaces`, `who_am_i` (REST mapping in [guide](memory-layer-for-agents-2026-11.md#mcp-tools--rest)) | [MCP → tools](https://supermemory.ai/docs/supermemory-mcp/mcp#tools) | GA | Zero-code agent memory | Docs |
| 92 | MCP Apps widgets (`select-space`, `guided-save`, `upload-file`, `memory-graph`), resources `supermemory://profile`/`spaces`, prompt `context` | [MCP → widgets](https://supermemory.ai/docs/supermemory-mcp/mcp#interactive-widgets) | GA | In-chat review before save | Docs |
| 93 | Plugins: Claude Code (session profile, direct recall per prompt, Stop-hook capture, `/supermemory:index`), Cursor (rules, skills, context-gatherer agent), Codex, OpenCode, OpenClaw, Hermes, Muse Code, Amp, Grok Bot; ChatGPT web and Claude Desktop connectors. Every plan incl. Free (2026-10-30) | [Claude Code](https://supermemory.ai/docs/integrations/claude-code) · [Cursor](https://supermemory.ai/docs/integrations/cursor) | GA | Coding-agent project memory | Docs |

## 12. Alternative runtimes

| # | Feature | Docs | Status | Agent use case | Verified? |
|---|---|---|---|---|---|
| 94 | SMFS: mount a namespace as a filesystem (FUSE/NFSv3), semantic `grep`, virtual `profile.md`, memory paths; `@supermemory/bash` `run_bash` tool for edge; Daytona/E2B/Vercel/Cloudflare guides | [SMFS](https://supermemory.ai/docs/smfs/overview) | Open source (July: alpha) | Agents that already think in `ls/cat/grep` | Docs · July live (legacy, alpha) |
| 95 | Supermemory Local (binary or Docker `supermemory/supermemory`, v0.0.9, local embeddings, full v5 API at `:6767`); Enterprise dedicated/air-gapped | [Self-hosting](https://supermemory.ai/docs/self-hosting/overview) · [Local vs Enterprise](https://supermemory.ai/docs/self-hosting/local-vs-enterprise) | GA (Local); self-host for cloud customers on Scale+ | Offline/regulated agents | Docs · July live (v0.0.5, HOLD) |

## 13. Evaluation and migration

| # | Feature | Docs | Status | Agent use case | Verified? |
|---|---|---|---|---|---|
| 96 | MemoryBench (LoCoMo, LongMemEval, ConvoMem; MemScore; custom providers/benchmarks) + migration (`npx supermemory migrate`, v5 rollout guide, from Mem0/Zep) | [MemoryBench](https://supermemory.ai/docs/memorybench/overview) · [v5 migration](https://supermemory.ai/docs/migration/api-v5) | GA | Prove memory helps before shipping | Docs · July live (MemoryBench OpenRouter adapter) |

## 14. Not in the product any more (or not documented)

- **Memory Router** (OpenAI-compatible proxy): there are no pages in the Nov 2026 docs index.
  The July lab rated it prototype-only. Treat it as **not a current capability**.
- **Hosted Company Brain**: discontinued 2026-09-25. The harness is open source.
- **`forgetAfter` on write**: not in the v5 add schema. Expiry in v5 is automatic, and
  `include.forgotten` can surface expired rows.
- **Search scoped to one `docId`**: not in v5. Use `GET document?include=chunks` instead.
- **SQL, joins, aggregates, lookup by primary key over memories**: Supermemory explicitly
  says it is not a system of record ([Rules](https://supermemory.ai/docs/concepts/rules)).

---

## Archive: July 2026 capability map (v3/v4). As of July 2026, superseded Nov 2026

> Kept verbatim for history (headings demoted one level). Live observations below were made
> against the legacy v3/v4 API in July 2026 and have **not** been re-run on v5.

> **As of Nov 2026:** this page records the July 2026 field lab, which ran against the
> v3/v4 API. Supermemory shipped a breaking, namespace-scoped **API v5 on 2026-10-07**.
> Claims marked _As of Nov 2026_ below are stale or changed. See
> [delta-2026-11.md](delta-2026-11.md) for the full diff. Nov 2026 live re-verification was
> **blocked** (the workspace key returned 401), so July observations are not re-confirmed.

This map covers the current product surface discovered through the official
[documentation index](https://supermemory.ai/docs/llms.txt), public repositories, generated
SDKs, and live probes. “Maturity” is a lab judgment, not a vendor status label.
Mixed labels mean the documented/source contract and the observed behavior were checked
separately; a local contract observation is never presented as a hosted framework run.

### Core API

_As of Nov 2026:_ the table below is the **legacy v3/v4** surface (still served, with no
published sunset). v5 equivalents, as Documented in the
[migration guide](https://supermemory.ai/docs/migration/api-v5.md):
`POST /ns/{ns}/document[/batch|/file]`, `PATCH /ns/{ns}/document/{id}`,
`POST /ns/{ns}/list/{documents|chunks|memories}` (cursor pagination),
`DELETE /ns/{ns}/memories[/semantic]`, `POST /ns/{ns}/search|profile`, and `DELETE /ns/{ns}?moveTo=`.
**No v5 replacement exists for:** direct memory creation, versioned memory update,
conversation upsert, `file-url`, `suggest-buckets`, or settings reset.

| Capability | Practical use | Evidence | Maturity judgment |
|---|---|---|---|
| Add text, URL, or file | Knowledge ingestion and extraction | **Documented / Observed:** [Add document](https://supermemory.ai/docs/api-reference/ingest/add-document); hosted text probe | Core |
| Batch/file upload | Bulk knowledge loading; current OpenAPI accepts 1–600 documents and files up to 50 MB | **Documented / Observed:** [Current OpenAPI](https://api.supermemory.ai/v3/openapi); hosted batch, Markdown multipart, and maximum-cardinality runs | Core; local 601 rejection and hosted 600/600 accepted, processed, reconciled, and searchable. One earlier 60-second acknowledgement timeout proves the need for stable IDs and inventory reconciliation; 50 MB/file-format boundaries remain pending. |
| Structured conversation upsert | Preserve roles and append a conversation by ID | **Documented / Observed:** [Conversation endpoint](https://supermemory.ai/docs/api-reference/ingest/ingest-or-update-conversation); hosted probe | Core |
| `customId` upsert | Stable application identity for a document | **Observed:** hosted probe returned the same document ID | Core, extraction semantics need regression tests |
| `dreaming=dynamic` | Group related content before memory creation | **Documented / Observed:** [Adding memories](https://supermemory.ai/docs/add-memories); repeated hosted batch probe | Asynchronous enrichment: small batches remained `dreaming` beyond 60–90 s and lacked the exact extracted fact in the extra check; use a direct confirmed-fact readiness fallback |
| `dreaming=instant` | Extract each document independently; extra documented operation | **Documented / Observed:** same source; hosted probe | Core |
| `taskType=superrag` | Index knowledge without generating personal memory facts | **Documented:** [SuperRAG](https://supermemory.ai/docs/concepts/super-rag) | Core |
| Direct v4 memory creation | Exact facts without extraction; up to 100 per call | **Documented / Observed:** [Direct creation](https://supermemory.ai/docs/api-reference/content-management/create-memories-directly); hosted probes | Core; profile can precede search visibility |
| Versioned memory update | Correct a fact while preserving history | **Documented / Observed:** [Update](https://supermemory.ai/docs/api-reference/content-management/update-a-memory-creates-new-version); hosted probe | Core |
| Forget one memory | Remove a fact from normal search | **Documented / Observed:** [Forget](https://supermemory.ai/docs/api-reference/content-management/forget-a-memory); hosted probe | Core |
| Agentic mass-forget | Natural-language deletion with dry-run | **Documented / Observed:** [Forget matching](https://supermemory.ai/docs/api-reference/content-management/forget-memories-matching-a-promptquery); hosted probe | Slow/variable; background workflow only |
| Memory expiry (`forgetAfter`) | Lease temporary context and cancel through versioned update | **Source-inspected / Observed:** current [OpenAPI](https://api.supermemory.ai/v3/openapi); hosted expiry/cancel probe | Core; explicit forget and expiry had different recovery behavior |
| Memory history/list | Inspect current administrative inventory and mutation lineage | **Source-inspected / Observed:** [Current OpenAPI](https://api.supermemory.ai/v3/openapi); hosted unfiltered three-version correction probe | Top-level entries represent current truth; the observed latest v3 entry nested history `[1, 2, 3]` with valid parent/root continuity. This corrects the earlier latest-only interpretation; test pagination/export and do not treat it as a compliance signature. |
| Document lifecycle | List, get, chunks, update, delete, processing state | **Documented / Observed:** [Document operations](https://supermemory.ai/docs/document-operations); hosted probes | Core; the 24-record run observed exact inventory while 16 records were still processing, then 24/24 done |
| Exact document chunks/file URL | Export ordered source chunks or obtain a temporary original-file URL | **Source-inspected / Observed:** [Current OpenAPI](https://api.supermemory.ai/v3/openapi); hosted meeting-file run | Ordered chunk citation and temporary HTTPS URL passed. Official changelog says URLs expire after 24 hours; never persist them in memory, prompts, traces, or logs. |
| Bulk exact document delete | Roll back a known import set without semantic selection | **Source-inspected / Observed:** [Current OpenAPI](https://api.supermemory.ai/v3/openapi); hosted ten-ID and six-by-100 rollback runs | Core for migration recovery; local 101-ID rejection, signed restart after 200 deletions, six exact 100-ID batches, idempotent completed replay, empty inventory, and negative search passed. Do not expose container-wide selectors to a model. |
| Organization settings/bucket suggestion | Inspect processing configuration and propose profile organization | **Source-inspected / Observed:** [Current OpenAPI](https://api.supermemory.ai/v3/openapi); hosted additive-schema run | Five suggestions passed current shape validation. One was reviewed/applied only after signed effective-schema capture and concurrent-drift rejection; never grant suggestions direct mutation authority. |

### Recall and profile

| Capability | Practical use | Evidence | Guidance |
|---|---|---|---|
| v3 document search | Source-oriented RAG with chunks, summaries, full docs | [Search](https://supermemory.ai/docs/search); hosted probe | Use when document grouping/citations matter. |
| v4 memory search | Low-token distilled fact recall | [v4 search](https://supermemory.ai/docs/api-reference/recall-search/search-memory-entries); hosted probe | Make `searchMode="memories"` explicit. |
| v4 hybrid search | Facts and raw chunks together | Same source; hosted probe | Best default for research/support questions. |
| v4 document mode | Raw source retrieval through v4 | Same source | Use when extraction would discard wording. |
| Metadata filters | AND/OR, scalar, string, numeric, array, negation | [Filtering](https://supermemory.ai/docs/concepts/filtering); seven-shape hosted matrix | Put tenant in container; use metadata for subsets. Dotted search keys worked despite doc ambiguity. |
| Reranking | Better result order for added latency | [Search](https://supermemory.ai/docs/search) | Enable selectively; benchmark quality gain. |
| Query rewriting | Broader query understanding for added latency | Same source | Use for difficult natural-language queries, not every turn. |
| Natural-language time windows (_As of Nov 2026: date phrases now **boost** rather than filter, per the 2026-10-15 changelog; re-run needed_) | Retrieve past, present, and future facts using phrases such as `last week` or `in August 2026` | [June 25 API changelog](https://supermemory.ai/changelog/api/); 10-case hosted matrix | Passed with rewrite off/on on a three-event corpus; provide trusted date/timezone and keep canonical event state elsewhere. |
| Aggregate results | Compress multiple memories into query-specific context | Current SDK/changelog and HandoffBoard probe contract | Useful for multi-agent boards; verify citations are not lost. |
| User profile | Stable, dynamic, bucketed, and query-specific context | [Profiles](https://supermemory.ai/docs/concepts/user-profiles); hosted probe | Excellent session-start primitive. |
| Profile buckets | Built-in preferences plus custom org/container categories | [Buckets API](https://supermemory.ai/docs/api-reference/profiles/get-profile-buckets); custom-bucket and schema-evolution hosted probes | Custom buckets persisted and classified the corrected fact. Treat evolution as additive schema: preserve container buckets, detect effective-key collision/drift, and remember organization buckets cannot be removed by a container update. |
| Inferred-memory review | Approve, decline, or undo generated inferences | [Memory review](https://supermemory.ai/docs/memory-review); endpoint/queue/negative-control and larger matrix | Add exact external authorization for sensitive personalization. Matched eight-document instant runs produced two one-parent candidates and then zero; dynamic produced none and remained pending. Ordinary-memory review returned 409. Generated-candidate approve/decline/undo remains pending. |

### Organization, isolation, and customization

| Capability | Notes |
|---|---|
| Container tags (_As of Nov 2026: called **namespaces** in v5; same pattern, now in the URL path, one per document_) | Strict namespace, current v4 singular field, 100 characters, pattern `^[a-zA-Z0-9_:-]+$`. A negative-control search returned zero. |
| Scoped keys | One- or multi-container key, expiry and rate-window controls, restricted endpoint set. Hosted single-scope and three-scope reads, cross-tenant denial, and immediate revocation were observed. A delegated-worker key returned `403` for cross-scope read/write, `401` after revocation, and `[200,200,429]` with `Retry-After` at a two-request limit. _As of Nov 2026:_ the auth page now documents `containerTags` and v5 allowed endpoints, at `/auth/scoped-key`. Prefer one short-lived container per user-facing or sandboxed worker. |
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

### Integration surfaces

| Surface | Best fit | Current assessment |
|---|---|---|
| TypeScript/Python SDKs | Typed direct API access | Generated clients are useful; pin and wrap them. |
| `@supermemory/tools` | Framework middleware and tool factories | Convenient; explicit client remains easier to audit. |
| Vercel AI SDK | TypeScript chat/agent apps | **Documented / Observed (local):** first-class wrapper; recall/capture identity contract passed locally. |
| OpenAI SDK/Agents | Function tools and middleware | **Documented / Reported / Observed (local):** wrapper issues are reports; fail-closed recall/capture contract passed locally. |
| LangChain/LangGraph | Existing graph/chain stacks | **Documented / Observed (local):** pre/post and graph-node contracts passed; preserve explicit container derivation. |
| Mastra/Agno/CrewAI/VoltAgent | Agent-framework adoption | **Documented / Observed (local):** Mastra/Agno/CrewAI hook contracts passed; VoltAgent remains source-only. |
| Microsoft Agent Framework | .NET/Python agents | Supported; a current issue reports Python dedup type problems. |
| Convex | Backend-integrated memory | **Documented / Observed (local):** action/mutation boundary contract passed; real Convex runtime remains untested. |
| Pipecat/Cartesia | Voice agents | Useful asynchronous memory path; current issue reports Python wrapper bugs. |
| n8n/Zapier/viaSocket | No/low-code automation | Good for ingest workflows, not a trust boundary. |
| MCP | Portable `memory`, `recall`, identity/profile context | **Source-inspected / Observed (local):** current monorepo surface mapped; strict tools and one-time authorized write contract passed. |
| Coding plugins | Automatic project/user recall and periodic capture | **Source-inspected / Observed (local):** user/project/custom session-hook contract passed; real auto-capture still deserves review. |
| Memory Router (_As of Nov 2026: removed from docs index; status unverified_) | Drop-in OpenAI-compatible proxy | Delta/full-history and direct API pool controls passed; Router-generated cross-session recall failed. Keep prototype-only. |
| Memory Graph UI | Explore documents, memories, relationships | Visualization, not evidence of a particular storage algorithm. |

The runnable [framework integration contracts](framework-integrations.md) cover the ten local
surfaces labeled above. They verify memory-boundary behavior, not compatibility with every
third-party package version; add the adopted runtime and version to CI before production.

Official integration pages currently include Vercel AI SDK, Microsoft Agent Framework,
Agno, OpenAI Agents, CrewAI, Convex, LangChain, LangGraph, Mastra, VoltAgent, Cartesia,
Pipecat, OpenAI, n8n, Zapier, viaSocket, Claude Memory, and several coding plugins. See the
[documentation index](https://supermemory.ai/docs/llms.txt) for the current list.

### Connectors

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

### Alternative runtimes

#### Self-hosted server

_As of Nov 2026:_ Local v0.0.9 and Docker images are available, so an upgrade drill is now possible (not run). v5 SDKs require ≥ v0.0.9.

**Documented / Source-inspected / Observed (local):** the local server exposes the hosted-style API with encrypted local storage, local or remote
embeddings, and a bring-your-own extraction model. The local edition is single-tenant and
does not include managed connectors/MCP. A v0.0.5 stopped snapshot, same-directory restart,
byte-identical clean restore, search/profile recovery, and exact deletion passed for direct
memory state. Production remains a HOLD on this macOS setup: parent shutdown returned signal
`-5`, detached workers required explicit reaping, a v3 ingest remained queued for 180 seconds,
and no newer release existed for a real upgrade drill. See
[self-hosting](https://supermemory.ai/docs/self-hosting/overview).

#### SMFS

**Documented / Source-inspected / Observed:** SMFS maps a container to filesystem semantics. The mount uses NFSv3 on macOS or FUSE on
Linux; the Bash tool provides a virtual shell for serverless agents. `memory.md`/`user.md`
are memory paths by default, other files use SuperRAG, `profile.md` is virtual, and plain
`grep` can become semantic. The lab validated the Python Bash tool, including write/read,
list, semantic search, and cleanup. It also found alpha quirks: delayed profile extraction
and a zero-byte list entry despite readable content. See [SMFS](https://supermemory.ai/docs/smfs/overview).

#### Consumer app and browser extension

_As of Nov 2026:_ hosted Company Brain was discontinued on 2026-09-25, and its harness is open source.

The app, Nova agent, extension, and memory graph let an individual collect and query
personal context without building an application. They share concepts with the developer
platform but should be evaluated separately for export, deletion, capture scope, and privacy.

### What is not a capability

- Supermemory is not a transactional database, queue, lock service, scheduler, or policy engine.
- Semantic similarity is not permission or identity verification.
- A graph visualization does not guarantee that every answer is graph-reasoned.
- A high benchmark score does not establish production quality without latency and context-token cost.
- Fail-open generation means availability can survive while memory correctness silently degrades.
