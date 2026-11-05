# Build patterns: things you can ship on Supermemory (Nov 2026, API v5)

Each pattern lists its namespace layout, write path, read path, and the exact v5
operations it uses, plus the gotcha that usually breaks it. Routes are from the live
[v5 OpenAPI](https://api.supermemory.ai/openapi.json). The background is in
[memory-layer-for-agents-2026-11.md](memory-layer-for-agents-2026-11.md). Python snippets use
the lab's dependency-free client [`supermemory_lab.v5.SupermemoryV5`](../src/supermemory_lab/v5.py),
whose methods map 1:1 to the official SDK calls (`supermemory.add(ns, {...})` in TS,
`client.add(ns, ...)` in Python).

> Live status: these designs are **docs- and spec-grounded**. Live v5 runs were blocked
> (401). The July 2026 lab built legacy versions of several of them, linked as
> "July precedent". Treat July numbers as legacy-API observations.

| # | Pattern | Core APIs | July precedent |
|---|---|---|---|
| 1 | [Personal agent memory](#1-personal-agent-memory) | profile, search(hybrid), add(id=session), instant facts, buckets | `run_evolving_preference_agent.py` |
| 2 | [Support bot with long-term preferences](#2-support-bot-with-long-term-customer-preferences) | per-customer ns + SuperRAG KB ns, profile filter, scoped keys | `run_enterprise_context_agent.py` |
| 3 | [Multi-agent shared memory](#3-multi-agent-shared-memory) | private + team namespaces, metadata author, publish step | `run_decision_council.py`, `run_corroborated_research_swarm.py` |
| 4 | [Research agent: corpus + recall](#4-research-agent-corpus--recall) | URL/file/batch SuperRAG, chunks + include.documents, rerank, web-crawler | `run_due_diligence_campaign.py` |
| 5 | [Coding-agent project memory](#5-coding-agent-project-memory) | plugins/MCP or repo namespace, decisions as documents, SMFS | `run_project_memory_os.py` |
| 6 | [Decision journal with app-owned lineage](#6-decision-journal-with-application-owned-lineage) | stable doc id per decision, PATCH, list memories | `run_governed_memory_curator.py` |
| 7 | [Voice agent caller memory](#7-voice-agent-caller-memory) | Pipecat/LiveKit, profile markdown, async add | — |
| 8 | [Adaptive tutor](#8-adaptive-tutor) | buckets (skills, goals), dynamic profile, date backfill | `run_adaptive_tutor.py` |
| 9 | [Account briefing from connectors](#9-account-briefing-from-connectors) | Gmail/Granola/Notion connectors, group, profile | `run_relationship_account_briefing.py` |
| 10 | [Memory transparency and consent UI](#10-memory-transparency-and-consent-ui) | list memories (cursor), get memory related, review queue, forget | `run_memory_transparency_agent.py` |
| 11 | [Erasure and identity merge](#11-erasure-and-identity-merge) | DELETE ns, `?moveTo=`, scoped-key revoke | `run_filter_erasure_agent.py` |
| 12 | [Cross-assistant memory with zero code](#12-cross-assistant-memory-with-zero-code) | hosted MCP, spaces, widgets | — |
| 13 | [Edge / sandbox agent with a memory filesystem](#13-edge--sandbox-agent-with-a-memory-filesystem) | SMFS mount, `@supermemory/bash` | SMFS alpha run |
| 14 | [Prove it: memory evals](#14-prove-it-memory-evals) | MemoryBench, lab blinded suite | `run_blinded_domain_100_benchmark.py` |

---

## 1. Personal agent memory

**Ship:** an assistant that knows the user's name, tone, timezone, and current projects
from turn one, and remembers new facts across restarts.

- **Namespaces:** `user_{userId}`, one per user.
- **Write:** after each turn, `add(ns, transcript, id=session_id)` with the growing
  transcript (same prefix → diff billing). Explicit "remember that…" goes through
  `add(ns, statement, id=f"fact:{slug}", dreaming="instant")`.
- **Read:** `profile(ns)` at session start (static + dynamic + buckets), then
  `search(ns, message, search_mode="hybrid", limit=5, threshold≈0.5)` per turn.
- **Structure:** `PUT /ns/{ns}/profile/buckets` with `work`, `goals`, `travel`, … The
  `preferences` bucket is always present.
- **Correction:** `PATCH /ns/{ns}/document/fact:{slug}` with the new statement.
- **Lab code:** `MemoryLayer` in [`memory_layer.py`](../src/supermemory_lab/memory_layer.py).

```python
layer = MemoryLayer(SupermemoryV5(transport), "user_42", session_id="2026-11-05-s1")
ctx = layer.session_start()                 # POST /ns/user_42/profile
prompt_ctx = layer.before_turn(msg).render()  # POST /ns/user_42/search
layer.after_turn(msg, reply)                # POST /ns/user_42/document  (id=session)
layer.remember_now("fact:tz", "User works in IST")   # dreaming=instant
layer.correct("fact:tz", "User moved; now works in PST")  # PATCH document
```

**Gotcha:** with default dynamic dreaming, a brand-new user's profile can be empty for
minutes. Reserve `instant` for confirmed facts, and do not use it for every turn (+1 op each).

## 2. Support bot with long-term customer preferences

**Ship:** a support agent that remembers each customer's plan, past issues, and
communication preferences, and answers policy questions from a shared knowledge base.

- **Namespaces:** `org:{customerOrg}:user:{userId}` per end user, plus `kb_{product}` for the
  knowledge base. These are separate because one request reads one namespace, and the KB
  must never shape a customer's profile.
- **Write:**
  - Tickets and chats go to the user namespace (`id=ticket:{id}`, `metadata.source="support"`).
  - KB articles go to `kb_*` with `taskType="superrag"` (5× cheaper, no memories).
- **Read (two parallel calls):** `profile(user_ns, filter=eq("source","support"))` + `search(kb_ns, q, search_mode="chunks", include={"documents": True})`
  for citations. Merge in the app.
- **Isolation:** the bot runtime gets a **scoped key** (`POST /auth/scoped-key` with
  `containerTags=[user_ns, kb_ns]`, `expiresInDays`, `rateLimitMax`). Mint it per
  conversation server-side.
- **Steering:** `organizationalContext` = "Customer-support assistant for Acme…";
  `supportingContext` per user namespace.

**Gotcha:** scoped keys are not read-only. If the bot must not delete, keep deletes behind
your own server-side tool rather than the scoped key.

## 3. Multi-agent shared memory

**Ship:** a crew (planner, researcher, coder, reviewer) where each agent has private
scratch memory and the team shares vetted decisions.

- **Namespaces:** `agent:{crew}:{role}` (private) and `team:{crew}` (shared).
- **Write:** agents `note()` to private by default. Promotion to shared is an explicit
  `publish()` with `metadata.author`, ideally after a reviewer agent or human approves it.
  This stops one agent from silently rewriting team truth.
- **Read:** `SharedMemoryRouter.recall()` searches both namespaces and merges by
  similarity, labelling each result `private` or `shared`.
- **Soft scoping inside team memory:** `metadata.kind` (`decision|finding|todo`) and
  `group={"kind": "decision"}` on writes, so new decisions build only on prior decisions.
- **Keys:** one scoped key per agent with `containerTags=[own_private, team]`.

**Gotcha:** there is no cross-namespace search. Fan-out cost is N searches per turn, so
keep N small (private + team + maybe org).

## 4. Research agent: corpus + recall

**Ship:** a research agent that ingests sources (links, PDFs, crawled sites), answers with
citations, and remembers what the *user* cares about across projects.

- **Namespaces:** `research:{projectId}` for the corpus, and `user_{id}` for researcher
  preferences ("prefers primary sources", "skip vendor blogs").
- **Ingest corpus:** URLs as content, files via `POST …/document/file`, bulk via
  `POST …/document/batch` (≤600) — all with `taskType="superrag"` and `metadata`
  (`source_type`, `year`, `venue`). For sites, use a **Web Crawler** connector (Scale+,
  weekly recrawl, unchanged pages skipped).
- **Findings** the agent concludes go in as normal documents (memory path) with
  `id=finding:{slug}`, so the graph links and updates them.
- **Read:** `search(corpus_ns, q, search_mode="chunks", rerank="order", include={"documents": True})`
  for grounded answers. Add `rewrite_query=True` for vague questions (+1 op each). Use
  numeric metadata filters for hard date windows, because dates in the query only *boost* ranking.
- **Steering:** `supportingContext` on the project namespace ("Papers on retrieval-augmented
  agents; focus on evaluation methodology").

**Gotcha:** keep documents medium-sized. Split 400-page reports by chapter so
dreaming can relate them.

## 5. Coding-agent project memory

**Ship:** Claude Code / Cursor / Codex agents that remember architecture, conventions, and
past fixes across sessions and across tools.

- **Fastest path:** install the official plugin (all plans, OAuth via
  `npx supermemory plugin`). The plugins load the project profile at session start,
  recall on each substantive prompt, capture turns on stop, and share **one repository
  container** across Claude Code, Codex, OpenCode, and Cursor (tagged `sm_scope: personal`).
  Run `/supermemory:index` once to seed architecture notes.
- **Custom path (your own coding agent):**
  - Namespace `repo:{org}:{repo}` (and optionally `repo:{org}:{repo}:user:{dev}`).
  - Write decisions and postmortems as documents with stable IDs (`adr:0007`,
    `incident:2026-11-01`) and `metadata.path`, `metadata.kind`.
  - Read the profile for conventions plus `search(memories)` for "have we seen this error before".
  - Self-host with Local (`npx supermemory local`, or Docker) when code cannot leave the
    machine. Plugins accept `baseUrl` + `apiVersion: "v5"` on server ≥0.0.9.
- **Filesystem flavour:** mount the namespace with SMFS so the agent uses `grep` (semantic
  by default) and `cat profile.md`.

**Gotcha:** don't ingest the whole repository as memory. Code is better served by the
agent's own tools. Ingest the *narrative*: why, decisions, gotchas.

## 6. Decision journal with application-owned lineage

**Ship:** an auditable "what did we decide and why" memory that survives v5's removal of
versioned memory updates.

- **Canonical ledger in your DB:** `decision_id`, `version`, `author`, `supersedes`,
  `approved_at`, `text_hash`.
- **Supermemory holds the current statement:** one document per decision
  (`id=decision:{id}`), `PATCH` on each new version, with `metadata.version`. The graph's
  `updates` relation keeps search on the latest truth (`isLatest`).
- **Read:** `search(memories)` for recall. Join to the ledger by document `id` for
  provenance (`include={"documents": True}` or `GET memories/{id}?include=documents`).
- **Audit view:** `list/memories` (cursor) + your ledger diff.

**Why:** July's versioned-memory chains (`PATCH /v4/memories`, parent/root lineage) are
legacy-only. In v5, lineage belongs to the application.

## 7. Voice agent caller memory

**Ship:** a phone or voice agent (Pipecat, LiveKit, Cartesia) that greets returning callers
with context.

- **Namespace:** `caller:{hashedPhone}`.
- **Read:** fetch the profile at call connect. Use `Accept: text/markdown` and paste it
  directly into the system prompt. Profile reads are not metered as searches in v5.
- **Write:** post the transcript with `id=call:{callId}` after hang-up (dynamic dreaming is
  fine because the next call is minutes or days away).
- **Latency:** the profile is one call. Skip per-utterance search unless needed (median
  recall is 187 ms per the pricing page; validate yourself).

## 8. Adaptive tutor

- **Namespace:** `learner:{id}`.
- **Buckets:** `skills` ("competencies mastered or being learned"), `goals`, `education`.
- **Write:** session transcripts plus graded attempts as short documents with
  `metadata.topic`, `metadata.score` (number), and `date` for imported history (backfill).
- **Read:** profile `dynamic` = "what they're working on now". Use
  `search(memories, filter=all_of(eq("topic","fractions"), {"field":"score","operator":"lt","value":0.6}))`
  to find weak spots.

## 9. Account briefing from connectors

- **Namespace:** `account:{crmId}`.
- **Connectors:** Gmail (Max+), Granola meeting notes (Pro+), Notion (Pro+), each created
  via `POST /ns/{ns}/connectors` with a narrow `selection` (labels, folders) and a
  `documentLimit`.
- **Read:** profile = relationship summary. `search(hybrid)` for "what did they say about
  pricing". `group` keeps meeting-derived facts separate from email-derived ones if needed.
- **Ops:** webhooks expire (7–30 days), so schedule `POST …/connectors/{id}/sync` as a backstop
  (409 means one is already running).

## 10. Memory transparency and consent UI

**Ship:** a "what the assistant knows about me" page.

- `POST /ns/{ns}/list/memories` with cursor pagination, and `include.forgotten` for an audit tab.
- `GET /ns/{ns}/memories/{id}?include=related,documents` for "why do you think this?".
- Inferred memories (`isInference`) go in a swipe-to-review queue:
  `GET /v3/container-tags/{ns}/inferred` → `POST …/inferred/{id}/review {action: approve|decline|undo}`.
- One-click forget: `DELETE /ns/{ns}/memories {ids}`. For a topic, use the semantic dry run, then the reviewed IDs.
- Visualize with the `@supermemory/memory-graph` React component.

## 11. Erasure and identity merge

- **Anonymous → signed-in:** `DELETE /ns/anon:{deviceId}?moveTo=user_{id}` (queued,
  returns `operationId`). Never put `moveTo` in a JSON body. The lab client makes that
  impossible (`delete_namespace(move_to=...)` sends no body).
- **Right to erasure:** `DELETE /ns/user_{id}` with an admin/owner key, then revoke the user's
  scoped keys (`DELETE /auth/scoped-key/{id}`). Shared documents are retained by design, so
  record that in your DPA.
- **Verify:** `GET /namespaces?q=user_{id}` shows it is gone. The lab suite's `cleanup`
  step does this check.

## 12. Cross-assistant memory with zero code

Add `https://mcp.supermemory.ai/mcp` to Claude (Settings → Connectors), ChatGPT (developer
mode), Cursor, or any MCP client. OAuth asks which **spaces** (namespaces) the client may
use. Tools: `search_memory`, `get_profile`, `add_memory`, `forget_memory`,
`list_documents`, `get_document`, `list_memories`, `list_spaces`, `who_am_i`. MCP Apps
clients also get `guided-save`, `upload-file`, `select-space`, and `memory-graph` widgets.
Manage connected apps and their scope on the console **Agents** page.

## 13. Edge / sandbox agent with a memory filesystem

- **Mount (FUSE/NFSv3):** for devcontainers, Docker, Codespaces, E2B, and Daytona.
- **No mount:** `@supermemory/bash` → `createBash()` returns a `run_bash` tool plus a tool
  description. Use it on Cloudflare Workers, Lambda, or Vercel. By default `user.md` and
  `memory.md` become memories. Configure more with `configureMemoryPaths`.
- **First call of every session:** `cat profile.md`.

## 14. Prove it: memory evals

Before shipping, measure memory against no memory on *your* tasks:

- **MemoryBench** (LoCoMo, LongMemEval, ConvoMem, MemScore). Plug in Supermemory and
  competitors with generated provider adapters. The lab has a tested
  [OpenRouter adapter](../integrations/memorybench-openrouter/README.md) from July.
- **Lab blinded domain suite:** [`run_blinded_domain_100_benchmark.py`](../experiments/run_blinded_domain_100_benchmark.py)
  scored 100/100 with memory vs 10/100 without in July (legacy API). It must be re-run on
  v5, because the hybrid default and the 0.3 threshold change what is retrieved.
- **This lab's feature suite:** [`run_memory_layer_lab_2026_11.py`](../experiments/run_memory_layer_lab_2026_11.py),
  29 exercises with shape-only evidence.
