# Current source inspection

Inspected on 2026-07-16:

- [supermemory monorepo at `8d92633`](https://github.com/supermemoryai/supermemory/tree/8d926332ab23aa5785def636aca9d0a52fea4a65)
- [MemoryBench at `118209a`](https://github.com/supermemoryai/memorybench/tree/118209a746d97d0d85e5a7234267f0b6962857e9)

The Supermemory commit was authored on the inspection date. The public tree contains clients,
docs, integrations, middleware, MCP, browser extension, and memory-graph packages; it does not
expose the hosted ingestion/search backend. Backend architecture claims therefore remain
documented or inferred, not source-verified.

The inspected upstream repository is licensed under
[MIT](https://github.com/supermemoryai/supermemory/blob/main/LICENSE). This field lab is also
MIT-licensed, but it is an independent implementation and research artifact. Links and commit
pins attribute upstream source behavior; hosted observations and original lab code are labeled
separately. MIT permission does not make the hosted proprietary extraction/search internals
available for audit.

## Agent integration behavior visible in source

### Profile-first middleware is the main integration pattern

The Microsoft Agent Framework context provider and OpenAI middleware both call `/v4/profile`.
They expose `profile`, `query`, and `full` modes, deduplicate static/dynamic/query results, and
inject formatted context before the model. This matches the live result: recent direct facts
appeared in the profile before hybrid search returned them.

- [Agent Framework context provider](https://github.com/supermemoryai/supermemory/blob/8d926332ab23aa5785def636aca9d0a52fea4a65/packages/agent-framework-python/src/supermemory_agent_framework/context_provider.py)
- [OpenAI middleware](https://github.com/supermemoryai/supermemory/blob/8d926332ab23aa5785def636aca9d0a52fea4a65/packages/tools/src/openai/middleware.ts)

### Caching is turn-local, not a durable memory replacement

`MemoryCache` is a 100-entry LRU keyed by container, optional thread, retrieval mode, and
normalized current message. It avoids duplicate retrieval during tool loops in one turn.
Cross-turn state still belongs in Supermemory.

- [Turn cache](https://github.com/supermemoryai/supermemory/blob/8d926332ab23aa5785def636aca9d0a52fea4a65/packages/tools/src/shared/cache.ts)

### The small AI SDK tools are explicit, not autonomous

The AI SDK package exposes `searchMemories` and `addMemory`. Search uses v3 document search with
a fixed chunk threshold; add accepts a short string. It does not implement write policy,
verification, forgetting, or tenant authorization.

- [AI SDK tools](https://github.com/supermemoryai/supermemory/blob/8d926332ab23aa5785def636aca9d0a52fea4a65/packages/ai-sdk/src/tools.ts)

### Integration defaults deserve review

Validate these in the exact package version you pin:

- One options type documents `addMemory` defaulting to `never`, while an OpenAI middleware
  implementation sets its default to `always`.
- The OpenAI wrapper can launch memory addition and retrieval concurrently. Do not expect the
  new write to affect that same retrieval.
- Some adapters fail open when retrieval/storage fails; others can fail the model request.
- Verbose logging can include memory previews or full formatted memory. Keep it off around
  private user context or add redaction.
- The forget helper calls v4 directly because the package's pinned SDK lacks that method.
  Pin SDK and integration-package versions together.

## MemoryBench internals and caveats

MemoryBench has a clean checkpointed pipeline: ingest, await indexing, search, answer, evaluate,
report. It supports LoCoMo, LongMemEval, and ConvoMem, and reports accuracy, search latency, and
context tokens as a three-part MemScore.

Useful implementation choices:

- Supermemory sessions are ingested as dated, escaped JSON documents.
- The provider waits for both document and memory status before search.
- Search uses hybrid mode, limit 30, summaries, and chunks.
- Results checkpoint per phase and resume after interruption.

Limitations in the inspected commit:

- Supermemory `clear()` is not implemented. Reused containers can contaminate comparisons.
- The indexing loop has no explicit overall timeout.
- Default concurrency is high: 100 ingest and 200 indexing.
- `options.threshold || 0.3` prevents a deliberate threshold of zero.
- Retrieval relevance uses an LLM judge; judge failure marks every result irrelevant.
- `recall@k` is effectively binary hit/no-hit and is not classical multi-relevant-item recall.
- A full run needs one of the supported judge/model credentials; OpenRouter is not a drop-in
  environment variable in this commit.

Practical fork backlog:

1. Use a fresh container per run and record it in every report.
2. Replace threshold truthiness fallback with a nullish fallback.
3. Add indexing timeout, retry budget, and 429 telemetry.
4. Start concurrency at 5–10 and scale from measured limits.
5. Add deterministic evidence-span scoring alongside the LLM judge.
6. Separate retrieval quality from answer-model accuracy.
7. Add OpenRouter as a first-class model and judge provider if it is the standard model path.
