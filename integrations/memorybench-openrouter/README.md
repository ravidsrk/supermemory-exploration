# MemoryBench OpenRouter adapter

This reviewed overlay adds OpenRouter as both an answering-model provider and an LLM judge to
the pinned upstream MemoryBench commit
[`118209a`](https://github.com/supermemoryai/memorybench/tree/118209a746d97d0d85e5a7234267f0b6962857e9).
It uses the existing OpenAI-compatible AI SDK dependency, so the overlay adds no package.

## Apply and verify

Start from a clean checkout at the exact pinned commit:

```bash
git clone https://github.com/supermemoryai/memorybench.git
cd memorybench
git checkout 118209a746d97d0d85e5a7234267f0b6962857e9
git apply /path/to/supermemory-exploration/integrations/memorybench-openrouter/memorybench-openrouter.patch
bun install --frozen-lockfile
bun test src/utils/models.test.ts src/judges/openrouter.test.ts
bunx tsc --noEmit
```

The convenience verifier performs the same checks and refuses a different upstream commit:

```bash
/path/to/supermemory-exploration/integrations/memorybench-openrouter/verify.sh \
  /path/to/memorybench
```

Both `OPENROUTER_API_KEY` and the supplied-project spelling `OPEN_ROUTER_KEY` are accepted.
Dynamic model identifiers use `openrouter:<provider/model>` so they cannot be mistaken for a
direct OpenAI, Anthropic, or Google credential path.

## One-question smoke run

Use one worker, a unique run ID, and a disposable Supermemory account/container scope:

```bash
export SUPERMEMORY_API_KEY=...
export OPENROUTER_API_KEY=...

bun run src/index.ts run \
  --provider supermemory \
  --benchmark locomo \
  --run-id sm-openrouter-YYYYMMDD \
  --limit 1 \
  --judge openrouter:openai/gpt-4.1-mini \
  --answering-model openrouter:openai/gpt-4.1-mini \
  --concurrency 1
```

The upstream Supermemory provider's `clear()` is not implemented at this commit. Read the exact
document IDs from each question's `phases.ingest.ingestResult.documentIds`, call
`client.documents.deleteBulk({ ids })`, and verify every subsequent `documents.get(id)` returns
404 or 410. Do not treat a successful CLI exit as proof of cleanup.

## What was observed

On 2026-07-17, the overlay passed four Bun contract tests, TypeScript compilation, a real
OpenRouter judge request, and a complete one-question Supermemory + LoCoMo run. All six
MemoryBench phases completed. The selected question retrieved zero results and scored
incorrect, so this smoke run validates wiring and failure visibility—not memory quality. The
19 ingested documents were bulk-deleted and independently verified absent.

The reviewed, secret-free record is
[`memorybench-openrouter-smoke.json`](../../evidence/memorybench-openrouter-smoke.json).

