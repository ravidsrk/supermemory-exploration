# Reproducible experiments

The curated results are in
[2026-07-16-field-lab.md](../evidence/2026-07-16-field-lab.md). This page explains how to
repeat and extend them safely.

## Local setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
cp .env.example .env.local
```

Fill only the required keys in ignored `.env.local`. Unit tests never require credentials:

```bash
python -m unittest -v
```

## Hosted core probe

```bash
supermemory-probe
supermemory-probe --with-llm
```

It creates unique `lab:` containers and tests direct facts, memory/hybrid/default search,
profile, isolation, update, forget, mass-forget dry-run, document ingestion/search/upsert,
conversation upsert, latency samples, optional OpenRouter generation, and document cleanup.

Raw output is written under ignored `.runs/`. It is redacted but still contains synthetic
content and hosted resource IDs; review before sharing.

Expected invariants:

- other-container search has zero results;
- update creates version 2 with a parent;
- precise forget removes the target from normal search;
- document `customId` returns the same document identity;
- cleanup makes document GET return 404;
- no key-shaped value appears in the report.

Do not make fixed latency an invariant. Compare distributions and server/client time separately.

## Memory Router probe

```bash
supermemory-probe --router-only
```

This forwards a synthetic fact through OpenRouter, waits for asynchronous memory, checks
same-conversation and same-user/new-conversation recall, sends a full-history control, checks
v4 memory visibility, and verifies another user does not receive the fact.

The first pass failed the positive recall controls. That is precisely why a control-based
probe belongs in the repository: a successful HTTP response is not a successful memory system.

## Connector entitlement probe

```bash
supermemory-probe --connector-only
```

The web crawler is the least risky connector to automate because it needs no user OAuth. The
probe uses `example.com`, a one-document limit, unique container, bounded polling, and cleanup.
On the current account it stops at the plan entitlement response.

Do not automate OAuth connection creation with real user accounts until redirect handling,
resource selection, container scope, deletion, and consent are designed.

## Scoped-key security probe

```bash
supermemory-probe --scoped-key-only
```

The probe creates two synthetic containers and a one-day key bound to only one. It checks an
allowed read, denied read, allowed write, denied write, revocation, a post-revocation read,
and admin cleanup. Denied operations and the revoked-key check are expected API errors.
The raw reporter redacts both ordinary secret-shaped fields and a bare `key` response field.

The 2026-07-16 run returned `403` for both cross-container operations and `401` immediately
after revocation; allowed operations and cleanup succeeded.

## Agent pattern demo

```bash
PYTHONPATH=src python examples/run_agent_patterns.py --pattern all
```

The demo intentionally leaves its synthetic `lab:agent:*` containers for dashboard
inspection. The 2026-07-16 live run produced:

- a personalized reminder in the requested concise style;
- a cited research answer identifying the latency improvement and untested concurrency;
- an aggregate handoff plus the underlying exact handoff memory;
- a revised 350 ms SLO with the original 500 ms decision as its parent.

Run one pattern with `--pattern personalized`, `research`, `handoff`, or `decision`.

## Multi-provider agent experiments

```bash
set -a
source .env.local
set +a
export PYTHONPATH=src:.

python experiments/run_advanced_agents.py intelligence
python experiments/run_advanced_agents.py tools
python experiments/run_advanced_agents.py release
python experiments/run_advanced_agents.py debug
python experiments/run_advanced_agents.py continuity
```

The live pass authenticated all supplied providers and ran five production-shaped agents.
Notable controls:

- competitive intelligence used Context.dev, Exa, public X/Reddit data, OpenRouter, and
  Supermemory in one trace;
- tool selection discovered and inspected without executing a mutation;
- generated patches ran in an egress-blocked, disposable SuperServe Python sandbox;
- the debugging transfer task used the same hidden test with and without remembered policy;
- support questions used isolated synthetic tenants and paired empty-tenant baselines;
- Vercel access stayed read-only and committed evidence omits project names.

See [the practical agent chapter](practical-agents.md) and the curated
[multi-provider evidence](../evidence/2026-07-16-multi-provider-agents.md).

## Disposable self-hosted probe

Follow the official [quickstart](https://supermemory.ai/docs/self-hosting/quickstart) in a
temporary directory. For non-interactive OpenAI-compatible extraction:

```bash
export SUPERMEMORY_DATA_DIR=/tmp/supermemory-lab-data
export SUPERMEMORY_PORT=6779
export OPENAI_API_KEY=your_provider_key
export OPENAI_BASE_URL=https://your-openai-compatible-provider.example/v1
export OPENAI_MODEL=your_model
supermemory-server
```

Use a disposable key/data directory, wait for the worker-ready log, then point this lab's
client at `SUPERMEMORY_BASE_URL=http://127.0.0.1:6779` with the local server's generated API
key. Test add → poll → memories/hybrid search → profile → restart → search again.

Before production, add:

- upgrade from the exact currently deployed version;
- backup/restore to a fresh host;
- large documents and configured content types;
- embedding model/dimension lock;
- queue pressure, restart during ingest, disk-full, and model outage;
- concurrent reads/writes and deletion durability.

The documented default local embedding is `Xenova/bge-base-en-v1.5` at 768 dimensions;
changing dimensions requires new data/re-ingestion. See
[configuration](https://supermemory.ai/docs/self-hosting/configuration) and
[embeddings](https://supermemory.ai/docs/self-hosting/embeddings).

## SMFS Bash tool probe

In a disposable Python 3.10+ environment:

```bash
python -m pip install supermemory-bash
```

Then create a unique container and test, in order:

1. `printf 'synthetic content' > /memory.md`
2. `cat /memory.md`
3. `ls -la /`
4. `sgrep 'semantic query' /`
5. `cat /profile.md` after bounded polling
6. `rm /memory.md`

The Python tool is a virtual shell. It supports documented built-ins, pipes, redirects,
conditionals, loops, and semantic `sgrep`; it is not a process sandbox. Current limitations
include no symlinks, `chmod`, `utimes`, `/dev/null` redirection, or binary upload. See the
[Python Bash tool docs](https://supermemory.ai/docs/smfs/bash-tool-python).

## Monthly regression record

For each run, add a dated evidence note containing:

- product/SDK/local-server versions and source commits;
- account plan/region if known;
- workload size and model;
- invariant pass/fail table;
- p50/p95/p99 client and server latency where sample size permits;
- context tokens and result count;
- observed changes from the previous run;
- open issue/changelog links explaining possible changes;
- no secrets, real PII, or customer content.

## Experiments still needed

- profile custom buckets and suggestions;
- inferred-memory creation/review/undo;
- `dreaming=dynamic` across related documents;
- filter operator truth table and negative cases;
- rerank/rewrite quality versus latency;
- batch upload and 50 MB boundary behavior;
- connector sync/update/delete on an entitled plan;
- expanded scoped-key endpoint/rate-limit matrix beyond the passing read/write/revoke probe;
- container merge/delete lifecycle;
- Router outage fail-open behavior and token headers;
- self-hosted upgrade/backup/restore and large-file regressions;
- SMFS mount concurrency and bidirectional 30-second sync;
- domain-specific MemoryBench run with a compatible judge key.
