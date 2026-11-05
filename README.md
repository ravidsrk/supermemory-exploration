# Memory Layer for Agents — Supermemory lab (Nov 2026)

A hands-on, source-cited lab for building the **memory layer of AI agents** on
[Supermemory](https://supermemory.ai), as of **2026-11-05**. It covers API v5 namespaces,
SDK 5.x, `@supermemory/tools` 3.0, the hosted MCP, coding-agent plugins, SMFS, and
Supermemory Local v0.0.9. It is the companion repo for the article *"Memory Layer for
Agents with Supermemory"*.

> **Live status (Nov 2026).** Every claim is grounded in primary sources: docs, the live v5
> OpenAPI, pricing, and the changelog. The live v5 suite is written and tested offline. Its
> 2026-11-05 run was **blocked** because the workspace key returned **401** on every route
> ([evidence](docs/evidence/experiments/2026-11-05-auth-and-sources.md)). No writes were
> made and no credits were used. Run it yourself with a valid key (see below).

## Start here

| If you want… | Read |
|---|---|
| The full mental model, architecture, patterns, gotchas, cost model | **[docs/memory-layer-for-agents-2026-11.md](docs/memory-layer-for-agents-2026-11.md)** |
| Every current capability (96 rows): docs URL, status, agent use case, verified? | **[docs/capability-map.md](docs/capability-map.md)** |
| 14 concrete things to ship, each tied to real v5 routes | **[docs/build-patterns.md](docs/build-patterns.md)** |
| What changed since the July 2026 (v3/v4) lab | [docs/delta-2026-11.md](docs/delta-2026-11.md) |
| The July 2026 deep-dive (legacy API, kept for history) | [docs/README.md](docs/README.md) · [verdict](docs/verdict.md) · [experiments](docs/experiments.md) · [archived README](docs/archive/README-2026-07.md) |

## Supermemory in 60 seconds (v5)

```text
documents in  ──▶  POST /ns/{namespace}/document   (text, URL, file, batch ≤600; stable id)
                         │  status: queued → … → done        (chunks searchable)
                         │  dreamingStatus: dreaming → done  (memories + profile ready)
                         ▼
three outputs ──▶  chunks   (RAG)        POST /ns/{ns}/search  searchMode: "chunks"
                   memories (graph)      POST /ns/{ns}/search  searchMode: "memories"
                   profile  (always-on)  POST /ns/{ns}/profile static · dynamic · buckets
                   (hybrid = memories ⊕ chunks, the v5 default; threshold default 0.3)
```

- A **namespace** (formerly container tag) is the hard isolation boundary. It lives in the
  URL, and each request touches exactly one.
- **No direct memory writes or memory updates in v5.** Ingest short statements with
  `dreaming: "instant"`, and correct facts by `PATCH`ing their source document.
- Forget by ID (`DELETE /ns/{ns}/memories`) or by meaning (`…/memories/semantic`, `dryRun`
  required).
- The same model is exposed through SDKs (TS/Python), `@supermemory/tools`, the MCP
  (`https://mcp.supermemory.ai/mcp`), plugins (Claude Code, Cursor, Codex, …), SMFS, and Local.

## What's in the lab

| Path | What |
|---|---|
| [`src/supermemory_lab/v5.py`](src/supermemory_lab/v5.py) | Dependency-free v5 client: one method per OpenAPI operation, documented limits checked locally, a `moveTo` footgun guard, and a cursor iterator |
| [`src/supermemory_lab/memory_layer.py`](src/supermemory_lab/memory_layer.py) | Reference agent harness: `session_start` (profile) → `before_turn` (hybrid search) → `after_turn` (append to stable session doc), plus `remember_now`, `correct`, `forget_reviewed`, and a multi-agent `SharedMemoryRouter` |
| [`src/supermemory_lab/memory_layer_lab.py`](src/supermemory_lab/memory_layer_lab.py) | 29-exercise live feature suite (ingest, dreaming, SuperRAG, files, search modes/threshold/filter/include, profile, buckets, updates, lists/cursor, forget, review queue, namespace move, cleanup) |
| [`experiments/run_memory_layer_lab_2026_11.py`](experiments/run_memory_layer_lab_2026_11.py) | Runner. Writes shape-only, secret-free evidence to `docs/evidence/experiments/` |
| [`tests/test_v5_memory_layer.py`](tests/test_v5_memory_layer.py) | 21 offline tests: paths, bodies, limits, fail-open hooks, diff-friendly appends, blocked-key behavior, end-to-end fake run |
| `docs/evidence/experiments/2026-11-05-*` | Nov 2026 evidence (auth probe, source snapshot, blocked suite run) |
| `evidence/2026-07-*`, other `experiments/run_*.py` | July 2026 legacy-API field lab (58 reference agents, benchmarks), unchanged |

## Run it

Python 3.9+ and no third-party dependencies.

```bash
python3 -m venv .venv && . .venv/bin/activate
python -m pip install -e .
PYTHONPATH=src:. python -m unittest -q          # offline, no key needed

cp .env.example .env.local                       # set SUPERMEMORY_API_KEY (never commit it)
PYTHONPATH=src python3 experiments/run_memory_layer_lab_2026_11.py --plan   # no network
PYTHONPATH=src python3 experiments/run_memory_layer_lab_2026_11.py          # live v5 suite
```

The live suite writes only into synthetic `lab:mla:<run>` namespaces and deletes them at
the end, then verifies they are gone. It never calls `/feedback`, never mints keys, never
changes organization settings, and never creates connectors. Expect a few cents of credits
per run on any plan (a handful of `instant` operations, ~30 searches, and a few KB of tokens).

## Primary sources

| Area | URL |
|---|---|
| Docs index (202 pages) | https://supermemory.ai/docs/llms.txt |
| v5 OpenAPI (live) | https://api.supermemory.ai/openapi.json |
| v5 API reference | https://supermemory.ai/docs/v5/api-reference/overview |
| v5 migration guide | https://supermemory.ai/docs/migration/api-v5 |
| Pricing | https://supermemory.ai/pricing |
| Changelog | https://supermemory.ai/changelog |
| MCP | https://supermemory.ai/docs/supermemory-mcp/mcp |
| Open-source monorepo | https://github.com/supermemoryai/supermemory |

## Secret safety

All `.env*` files except `.env.example` are git-ignored. Scripts redact authorization
headers and registered secret values, and evidence records only shapes, counts, and
status codes. If a key was ever pasted somewhere untrusted, rotate it.

## License

[MIT](LICENSE) © 2026 Ravindra Kumar. This is an independent exploration, not affiliated
with Supermemory. The upstream [Supermemory repository](https://github.com/supermemoryai/supermemory)
is MIT-licensed.
