# 2026-11-05: auth probe and primary-source snapshot (Memory Layer lab)

Secret-free record supporting [docs/capability-map.md](../../capability-map.md) and
[docs/memory-layer-for-agents-2026-11.md](../../memory-layer-for-agents-2026-11.md).

## Credential status (read-only probes, ~15:30 UTC)

`SUPERMEMORY_API_KEY` was present in the workspace environment, well-formed (`sm_` prefix,
90 chars). Its value was never printed or written. Every probe was a read-only `GET`:

| Probe | HTTP |
|---|---|
| `GET /ns` (v5) | 401 |
| `GET /namespaces` (v5) | 401 |
| `GET /organization` (v5) | 401 |
| `GET /connectors` (v5) | 401 |
| `POST /v3/documents/list` (legacy) | 401 |
| `GET /organization` with `x-api-key` header instead of Bearer | 401 |
| `GET /v5/organization` (wrong prefix, control) | 404 `No route matches` (v5 has no `/v5` prefix) |
| `GET https://mcp.supermemory.ai/mcp` unauthenticated | 401 (expected: OAuth) |
| `GET https://supermemory.ai/docs/mcp` (docs MCP) | 200 |

**Conclusion:** the key is rejected on every surface, legacy and v5, which matches the
earlier same-day refresh ([evidence/2026-11-05-v5-contract-refresh.md](../../../evidence/2026-11-05-v5-contract-refresh.md)).
This is a credential problem, not an API outage. No resources were created, so nothing
needs cleanup. Credits used: **0** (all requests were rejected before metering).

## Primary sources fetched

| Source | Result |
|---|---|
| `https://api.supermemory.ai/openapi.json` | 200, `info.version` 5.0.0, 22 paths / 33 operations, sha256 prefix `19be0d4bc1b4f9da` (unchanged from the morning refresh) |
| `https://supermemory.ai/docs/llms.txt` | 200, 202 unique page URLs, all fetched |
| `https://supermemory.ai/pricing` | 200: Free $0 ($5 credits), Pro $19 ($20), Max $100 ($130), Scale $399 ($600), Enterprise custom |
| `https://supermemory.ai/changelog` and `/changelog/api/` | 200, latest entry 2026-11-02 (cursor pagination) |

Raw pages were not committed (vendor content). Re-fetch them to reproduce.

## Live suite

[2026-11-05-memory-layer-lab.md](2026-11-05-memory-layer-lab.md): 29 exercises, all
`blocked` at preflight (401), with no writes attempted.
