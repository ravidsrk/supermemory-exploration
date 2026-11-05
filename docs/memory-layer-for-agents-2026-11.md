# Memory Layer for Agents with Supermemory (Nov 2026)

A field guide to using Supermemory as the memory layer of an AI agent, written against the
product as documented on **2026-11-05**: API v5, SDK 5.x, `@supermemory/tools` 3.0, hosted
MCP, plugins, SMFS, and Local v0.0.9. Every claim links to a primary source. The
[capability map](capability-map.md) has the full 96-row coverage table, and
[build-patterns.md](build-patterns.md) turns this into shippable designs.

> **Verification status.** Live v5 runs in this lab were **blocked**: the workspace key
> returned 401 on every route ([evidence](evidence/experiments/2026-11-05-memory-layer-lab.md)).
> Statements here are **Documented** or **Spec** (checked against the live OpenAPI) unless
> marked **July live (legacy)**, meaning observed on v3/v4 in July 2026. Owner action: run
> `PYTHONPATH=src python3 experiments/run_memory_layer_lab_2026_11.py` with a valid key.

---

## 1. The one-paragraph version

You send Supermemory **documents**: chat transcripts, notes, files, URLs, connector items.
It gives you back three different things from the same input, inside one **namespace**:
**chunks** (grounding for RAG), **memories** (atomic facts in a temporal graph that
updates, extends, derives, and forgets), and a **profile** (a compact static + dynamic
summary for always-on context). An agent reads the profile once per session, searches per
turn, and writes the conversation back under a stable session `id`. Everything else in the
product refines one of those three motions.

## 2. Architecture

```text
                ┌──────────────────────── your agent harness ────────────────────────┐
  user ──turn──▶│ session_start ─▶ profile()           (static + dynamic + buckets)  │
                │ before_turn   ─▶ search(hybrid)      (memories ⊕ chunks, ≤ limit)  │──▶ LLM
                │ after_turn    ─▶ add(id=session)     (append → diff-billed)        │
                │ tools         ─▶ remember_now / correct / forget_reviewed          │
                └───────────────────────────────┬─────────────────────────────────────┘
                                                │ HTTPS  /ns/{namespace}/…
┌───────────────────────────────────────────────▼───────────────────────────────────────┐
│ Supermemory (one namespace = one dedicated vector index = one hard boundary)          │
│                                                                                       │
│  document ─▶ queued → extracting → chunking → embedding → indexing → done (status)   │
│                │                                                                      │
│                ├──▶ chunks ──────────────────────────────▶ searchMode: "chunks"       │
│                └──▶ dreaming (dynamic | instant) ─▶ memories (dreamingStatus)         │
│                         facts · preferences · episodes                                │
│                         updates / extends / derives · isLatest · isInference          │
│                         auto-forget: expiry · contradiction · noise                   │
│                                   └──▶ profile: static · dynamic · buckets            │
└───────────────────────────────────────────────────────────────────────────────────────┘
```

Sources: [How it works](https://supermemory.ai/docs/concepts/how-it-works),
[Graph memory](https://supermemory.ai/docs/concepts/graph-memory),
[Profiles](https://supermemory.ai/docs/concepts/user-profiles).

**Two clocks matter.** `system.status = done` means *chunks* are searchable.
`system.dreamingStatus = done` means *memories and profile* reflect the document. Under the
default `dreaming: "dynamic"`, the second clock can lag by minutes. On a fresh namespace the
profile can be empty for "several minutes"
([Add context → processing modes](https://supermemory.ai/docs/ingestion/add-memories#processing-modes)).
Most "Supermemory forgot what I just said" bugs come from reading memories before the
second clock finishes.

## 3. Memories vs documents vs chunks vs profile

| | Document | Chunk | Memory | Profile |
|---|---|---|---|---|
| What | Raw input you send | Slice of a document | Extracted atomic fact | Synthesized summary of memories |
| Who maintains it | You (add / PATCH / delete) | Pipeline | Graph (updates/extends/derives/forgets) | Pipeline |
| Read with | `GET document`, `list/documents` | `search(chunks\|hybrid)`, `list/chunks` | `search(memories\|hybrid)`, `list/memories`, `GET memories/{id}` | `POST profile` |
| Personal? | No | No | Yes | Yes |
| Changes over time | Only when you change it | With document | Yes, temporal: `isLatest` | Yes |
| Good for | Source of truth, citations | RAG grounding | "What's true about X now" | Always-on context every turn |
| Cost to create | Tokens (memory or SuperRAG rate) | Included | Included in memory rate; `instant` +1 op | Free to read in v5 |

Supermemory's own placement test ([Rules](https://supermemory.ai/docs/concepts/rules)):
things a colleague would *remember* go to memory and profile. Things a colleague would
*look up* go in as documents and are recalled with chunk search. Things queried by ID or
summed go in **your database**. Instructions every request needs verbatim go in the
**system prompt**.

## 4. When to use which feature

| You need… | Use | Why / watch out |
|---|---|---|
| Per-user (or per-agent) memory | One namespace per user: `user_{id}` or `org:{o}:user:{u}` | Strict per-index isolation; metadata is *not* a security boundary |
| Save a conversation | `add(ns, transcript, id=session_id)`, repeated with the same prefix | Diff billing; dynamic dreaming groups turns into coherent units |
| "Remember this now" (confirmed fact) | `add(ns, "short statement", id=fact_id, dreaming="instant")` | v5 has **no direct memory write**; this is the documented replacement (+1 op) |
| Correct a fact | `PATCH /ns/{ns}/document/{fact_id}` with new content | v5 has **no memory update**; graph `updates` + `isLatest` do the rest |
| Reference corpus (policies, docs) | `taskType: "superrag"` | 5× cheaper, does not pollute the user's profile |
| Per-tenant extraction steering | `supportingContext` on namespace (≤1,500) | Org-wide steering is `organizationalContext` |
| Keep sub-teams' facts separate in one namespace | `metadata` on write + `group` (filtered writes) + `filter` on read | Soft scoping only |
| Always-on context | `profile()` once per session; cache short-TTL | Not metered as search in v5 |
| Per-turn context | `search(hybrid, limit 5–10, threshold ~0.5–0.6)` | Branch on `memory` vs `chunk` |
| Precise personal facts | `searchMode: "memories"` | Filter out `isInference` if you need stated facts only |
| Grounded answers with citations | `searchMode: "chunks"` + `include.documents` | Chunk size is a legacy org setting |
| Explain *why* | `include.related` or `GET memories/{id}?include=related,documents` | Parents/children/siblings |
| Topic-structured profile | Profile buckets (`PUT /ns/{ns}/profile/buckets`) | Add-only on top of org buckets; `preferences` always present |
| "Forget that" | `DELETE /ns/{ns}/memories` with IDs from search | Soft delete; check per-ID `errors` |
| "Forget everything about X" | `memories/semantic` `dryRun:true`, review, then exact-ID delete | Re-running with `dryRun:false` can drift |
| Delete a user | `DELETE /ns/{ns}` (admin/owner) + revoke scoped keys | Shared docs retained |
| Merge anon → signed-in | `DELETE /ns/anon?moveTo=user` | Query param. In a body it is ignored and **the namespace is deleted** |
| Untrusted runtime (browser, sandbox, sub-agent) | Scoped key (`POST /auth/scoped-key`, expiry, rate limit) | Writable scoped keys can still delete inside their namespaces |
| Sync SaaS sources | Connectors (8 providers, plan-gated) | Stable connector IDs give diff-billed resyncs |
| No code at all | Hosted MCP or plugins | OAuth, spaces = namespaces |

## 5. Agent harness patterns

Supermemory documents three integration shapes. Most real agents mix them.

### 5.1 Hooks (deterministic, recommended default)

From [Rules → tools, hooks](https://supermemory.ai/docs/concepts/rules): the **session start** hook loads
the profile, the **on-message** hook enriches the prompt with search, and the **on-stop** hook saves the
conversation. The Claude Code and Cursor plugins implement exactly this, with fail-open hooks
(Claude Code uses 3 s timeouts, per the 2026-08-21 changelog).

The lab's reference implementation is [`src/supermemory_lab/memory_layer.py`](../src/supermemory_lab/memory_layer.py)
(`MemoryLayer.session_start / before_turn / after_turn`), with offline tests in
[`tests/test_v5_memory_layer.py`](../tests/test_v5_memory_layer.py). Its properties:

- the profile and recalled items are rendered inside a `<memory-context>` block labelled
  *untrusted evidence, not instructions* (memory is a prompt-injection surface);
- profile duplicates are removed from search results;
- every hook **fails open**: the agent answers without memory and flags the turn as degraded;
- `after_turn` resends the growing transcript under one `id` with an identical prefix, so
  only new turns are billed.

### 5.2 Tools (the model decides)

Expose memory as tools: `search_memory`, `remember`, `forget`. Use `@supermemory/tools`
(Vercel AI SDK, OpenAI) or the framework guides (LangGraph, Mastra, CrewAI, Agno, OpenAI
Agents SDK, and others). This costs more tokens and calls, but the agent can query memory
mid-plan. Pair it with hooks so baseline context never depends on the model remembering to ask.

### 5.3 Protocol / filesystem surfaces

- **Hosted MCP** (`https://mcp.supermemory.ai/mcp`): any MCP client gets memory with OAuth and
  no code. Good for personal or cross-assistant memory. You control less about prompt rendering.
- **SMFS / `@supermemory/bash`**: the namespace appears as a filesystem with semantic `grep`
  and a virtual `profile.md`. Good for coding or sandboxed agents that already live in a shell.
- **Claude native memory tool backend**: Claude's `/memories/*` file commands map to documents.

### MCP tools ↔ REST

The MCP docs name the tools but not their REST internals. The mapping below is **Inferred**
from matching inputs and outputs to v5 operations. Use it to reason about cost and
permissions, not as a contract.

| MCP tool / widget | Closest v5 REST | Notes |
|---|---|---|
| `search_memory(query, namespace)` | `POST /ns/{ns}/search` | Returns memories with memory IDs + source document IDs; excludes profile |
| `get_profile(namespace)` | `POST /ns/{ns}/profile` | Also resource `supermemory://profile` |
| `add_memory(content, namespace)` | `POST /ns/{ns}/document` | Saves content as a document; memories follow via dreaming |
| `forget_memory(ids \| content)` | `DELETE /ns/{ns}/memories` (ids); content = exact-text match after preview | Never a broad semantic delete without a match |
| `list_documents(page, limit)` | `POST /ns/{ns}/list/documents` | MCP max 50 per page (REST 100) |
| `get_document(documentId)` | `GET /ns/{ns}/document/{id}` | |
| `list_memories(page, limit)` | `POST /ns/{ns}/list/memories` | Includes versions and source doc IDs |
| `list_spaces` | `GET /namespaces` | Spaces = namespaces the OAuth grant can see |
| `who_am_i` | no public v5 route (scoped keys may call `/session`) | Identity, role, scope, active space |
| `guided-save` / `upload-file` widgets | `POST /ns/{ns}/document` / `…/document/file` | Human confirms before write |
| `memory-graph` widget | list documents/memories + Memory Graph component | |
| prompt `context` | profile of active + up to 3 recent spaces | |

## 6. Writing memory well

1. **Send what you'd tell a human.** Send unstructured narrative, not database rows. Store
   "the customer disputed invoice #4821 and churned", not the invoice table.
2. **Do not pre-summarize with your own LLM.** The extractor knows what it already knows,
   and pre-summaries lose the signal it uses for updates/extends/derives.
3. **One stable `id` per session.** If you have no session ID, use a time window (the docs
   suggest a 4-hour bucket). Keep the prefix identical so diffing works.
4. **Medium-sized documents.** 400k+ tokens is supported but yields worse learnings.
   Ingest sequentially within a namespace, because order drives `updates`.
5. **`dynamic` in production, `instant` only when the next step reads memory.**
6. **Steer extraction** with `organizationalContext` (org) and `supportingContext`
   (namespace): who is this about, what matters, what to ignore.
7. **`superrag` for anything that is reference, not about the user.**
8. **Metadata for soft dimensions** (source, team, kind, priority) and `group` so new facts
   only build on the right subset.

## 7. Reading memory well

- **Profile first, search second.** Search misses facts that are relevant to *every* turn
  but semantically close to none, such as name, pronouns, timezone, or tone
  ([Profiles → non-literal matching](https://supermemory.ai/docs/concepts/user-profiles)).
- **Pick the mode on purpose.** `hybrid` is the v5 default. `memories` for personalization,
  `chunks` for grounding.
- **Set `threshold` explicitly.** v5 defaults to 0.3 (v4: 0.6), and the docs' chatbot
  example uses 0.6. Measure on your data. The lab suite records a 0.3/0.6/0.8 sweep once a
  key works.
- **Embrace a little noise.** About 10 tokens per fact (per Supermemory), so 50 facts is
  ~500 tokens. Distinctive details are what make personalization feel real.
- **Trust levels.** Separate `isInference: true` (derived) from stated facts, and run the
  [review queue](https://supermemory.ai/docs/recall/memory-review) for high-stakes domains.
- **Dates boost, they don't filter** (since 2026-10-15). If you need a hard window, use
  numeric metadata (`created_ts gte …`).
- **One namespace per request.** Multi-scope recall (private + team + org) is N calls
  merged in your app. See `SharedMemoryRouter` in the lab.

## 8. Keeping memory true: updates, corrections, forgetting

| Mechanism | Trigger | Effect |
|---|---|---|
| Graph `updates` | New contradicting fact ingested | Old fact stays for history; `isLatest` moves to the new one |
| Graph `extends` | New detail | Both valid |
| Graph `derives` | Pattern across facts | New `isInference: true` memory; reviewable |
| Auto-forget | Expiry ("exam tomorrow"), contradiction, noise | Excluded from search unless `include.forgotten` |
| Document `PATCH` (content) | You correct the source | Full reprocess; memories follow |
| Document delete | You remove a source | Derived memories removed with it |
| Forget by ID | User says "forget that" | Soft delete; per-ID errors |
| Semantic forget | "Forget everything about X" | `dryRun` preview → exact IDs. ≤100 per request, ops-metered |
| Review queue | Inferred memory | approve → stated; decline → forgotten; undo |
| Namespace delete | Erasure request | Permanent; shared docs retained |

v5 removed direct memory create and versioned memory update. The July lab's
"versioned decision journal" pattern must now keep **lineage in your own database** and
treat Supermemory documents as the current statement of each fact (one document `id` per
fact or decision, PATCHed on change). See [build-patterns.md §6](build-patterns.md#6-decision-journal-with-application-owned-lineage).

## 9. Multi-tenancy and security

- **Namespace = hard boundary.** Each has its own vector index. API keys and members can be
  restricted to namespace sets (403 outside the set, 403 on writes to read-only).
- **Scoped keys** for anything you don't fully trust: browser clients, sandboxes, sub-agents,
  third-party plugins. Set `expiresInDays` and `rateLimitMax`. Scoped keys cannot read
  billing, change org settings, or mint keys.
- **Not read-only by default.** A writable scoped key can delete documents and forget
  memories inside its namespaces.
- **Erasure:** namespace per user → `DELETE /ns/{ns}` → revoke keys
  ([Security](https://supermemory.ai/docs/overview/security)).
- **Compliance:** SOC 2 Type II, GDPR, HIPAA BAA on Scale/Enterprise. Self-host on
  Scale/Enterprise, air-gap on Enterprise ([Pricing](https://supermemory.ai/pricing)).
- **Prompt injection:** memories and chunks are user-influenced text. Render them as quoted
  evidence, never as instructions (the July lab's intake-firewall and 100-case suite showed
  zero bypasses with that discipline, **July live (legacy)**).

## 10. Cost model

Live rate card ([pricing](https://supermemory.ai/pricing), same on every plan):

| Meter | Rate |
|---|---|
| Memory tokens, text / rich | $5 / $10 per 1M SM tokens |
| SuperRAG tokens, text / rich | $1 / $2 per 1M SM tokens |
| Search queries | $5 per 1M queries |
| Operations (instant dreaming, rerank, aggregate, rewrite, semantic-forget rounds) | $100 per 1M operations |
| Profile (v5) | not metered as a search query |

Plans: **Free** $0 ($5 credits/mo), **Pro** $19 ($20), **Max** $100 ($130), **Scale** $399
($600), **Enterprise** custom. Included credits reset monthly. Top-ups never expire.
`402` means the balance is out, `403` means the plan is too low for a feature
([Billing](https://supermemory.ai/docs/overview/billing)).

**Worked example (illustrative arithmetic, not a quote).** A personal agent with 10,000
daily users, 20 turns each, and ~100 new tokens per turn appended to a session document:

- ingest: 10,000 × 20 × 100 = 20M new memory tokens/day → **$100/day**
  (diff billing means you pay for the 100 new tokens, not the whole transcript);
- search: 200,000 queries/day → **$1/day**;
- profile at session start: **$0** metered;
- if every turn used `dreaming:"instant"`: +200,000 ops → **+$20/day**. Use it only for
  confirmed facts.

Takeaway: **ingested tokens dominate**. The two biggest levers are (1) the SuperRAG rate for
reference content and (2) never re-sending unchanged content under a new `id`.

## 11. Gotchas (all documented)

1. **No `/v5` prefix.** Routes are `/ns/{ns}/…`. `GET /v5/organization` → 404.
2. **`moveTo` in a JSON body is ignored and the source namespace is permanently deleted.**
   Send it as a query parameter.
3. **Unknown query/body params return 400** on search, add, and list. Pagination for list
   goes in the query string. Filter/include go in the body.
4. **Search defaults changed**: `hybrid` and `0.3` in v5 (v4: `memories` and `0.6`). Pin
   them when comparing.
5. **`searchMode: "documents"` is now `"chunks"`.** `containerTag`→path, `customId`→`id`,
   `entityContext`→`supportingContext`, `filterByMetadata`→`group`, `documentDate`→`date`.
6. **Dynamic dreaming lag**: `status=done` ≠ memories ready. Poll `dreamingStatus`. The
   Python SDK 5.0.0 does not expose it (TS 5.0.1 neither), so use raw HTTP.
7. **Deletes refuse documents still processing.** They show up in `errors`, and HTTP 200 can
   carry partial failures.
8. **Semantic forget drift**: a second `dryRun:false` call re-matches. Apply reviewed IDs instead.
9. **The review action is `decline`**, not `reject`. Review routes still live under
   `/v3/container-tags/{ns}/…`.
10. **Multipart `metadata` is a JSON string.**
11. **Metadata keys are literal**: `customer.plan` is one key. Values cannot be nested.
12. **Filter limits**: 5 nesting levels, 200 operands per group.
13. **One namespace per request**: no `containerTags[]` fan-out in v5 (scoped-key minting
    still takes `containerTag(s)`).
14. **Scoped-key endpoint** is `/auth/scoped-key` (no `/v3`).
15. **Org buckets are console-only**. Namespace buckets are add-only and cannot shadow org names.
16. **Some settings are still legacy-only** (`chunkSize`, connector OAuth branding via
    `PATCH /v3/settings`), and SDK 5.x has no `settings` resource.
17. **Connector webhooks expire** (Drive/Gmail 7 days, OneDrive 30), so keep manual `sync`
    as a fallback.

## 12. Trade-offs and when *not* to use it

| Choose Supermemory when | Prefer something else when |
|---|---|
| You need personal, temporal memory that updates itself | You need exact, transactional state (use your DB) |
| You want RAG + memory + profile from one ingest | You need joins, aggregates, or lookups by primary key |
| Multi-tenant isolation must be structural | You cannot send data to a third party and cannot self-host |
| Time-to-value matters (MCP/plugins/middleware) | You need deterministic, audit-signed fact lineage (keep it yourself) |
| Agents in many harnesses must share memory | Sub-second write→read consistency of *memories* is mandatory (dynamic lag; instant costs ops) |

The July lab's verdict still holds and gets stronger in v5: **Supermemory is a context
system, not a system of record.** Keep canonical state and lineage in your application, and
use Supermemory for recall, personalization, and grounding.

## 13. Migration context (v3/v4 → v5)

v5 shipped 2026-10-07. v3/v4 are still served with no published sunset. `npx supermemory
migrate` drives a coding agent through the change, and the
[rollout guide](https://supermemory.ai/docs/migration/api-v5-rollout) recommends per-domain
flags, shadow calls, and pinning changed defaults. Full July→Nov diff:
[delta-2026-11.md](delta-2026-11.md).

## 14. Verified vs docs-only (this lab, Nov 2026)

- **Live-verified on v5:** none. The key was rejected (401) on `/ns`, `/namespaces`,
  `/organization`, `/connectors`, and legacy `/v3`. Zero writes, zero credits
  ([auth evidence](evidence/experiments/2026-11-05-auth-and-sources.md)).
- **Reachability:** hosted MCP endpoint responds (401 unauthenticated, as expected for
  OAuth). The docs MCP responds 200.
- **Spec-verified:** 47 capability rows checked against the live OpenAPI (routes, enums,
  defaults, limits).
- **Legacy live (July 2026):** 22 rows have a v3/v4 observation. Treat them as hypotheses for v5.
- **Ready to run:** a 29-exercise suite covering ingest, both dreaming modes, SuperRAG, URL,
  batch, file, search modes/threshold/filter/include, profile, buckets, append, PATCH,
  metadata-only PATCH, lists and cursors, document/memory gets, memory counts, forget by ID,
  semantic forget, review queue, namespace settings/move, org, connectors, and cleanup.
