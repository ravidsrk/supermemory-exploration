# 2026-11-05: v5 contract refresh (docs diff + blocked live probe)

Curated, secret-free record for the November 2026 refresh. Synthesis lives in
[docs/delta-2026-11.md](../docs/delta-2026-11.md).

## Source fetch (2026-11-05, ~14:50 UTC)

| Artifact | Result | sha256 prefix |
|---|---|---|
| `https://api.supermemory.ai/v3/openapi` (identical to `/v4/openapi`) | 200, OpenAPI 3.1, `info.version` 3.0.0, 33 paths / 42 ops | `c44368028a8f2d19` |
| `https://api.supermemory.ai/v5/openapi` (identical to root `/openapi.json`) | 200, `info.version` 5.0.0, 22 paths | `19be0d4bc1b4f9da` |
| Wayback `20261007200753` of `/v3/openapi` | 32 paths / 41 ops | `c1e8a19ef83b2378` |
| Wayback `20260218000034` of `/v3/openapi` | 26 paths / 35 ops | `26d7cf702089a06c` |
| `https://supermemory.ai/docs/llms.txt` | 200; v5 reference + 11 migration guides; no Memory Router entries | — |
| `https://supermemory.ai/docs/memory-router/overview.md` | 200 but body is the **Vercel AI SDK** page | — |

Raw specs were not committed; re-fetch them to reproduce.

### Legacy path diff

- Oct-07 → Nov-05: **added** `POST /feedback`; nothing removed.
- Feb-18 → Nov-05: added `/feedback`, `/v3/container-tags/list`, `/v3/container-tags/merge/{mergeId}`,
  `/v3/documents/{id}/chunks`, `/v3/documents/{id}/file-url`, `/v3/settings/reset`,
  `/v3/settings/suggest-buckets`, `/v4/memories/forget-matching`, `/v4/memories/list`,
  `/v4/profile/buckets`; removed `/v3/graph/{bounds,stats,viewport}`.
- Schema-level Oct-07 → Nov-05: cursor pagination (`cursor`, `pagination.hasMore`,
  `pagination.nextCursor`) on `/v3/documents/list`, `/v4/memories/list`, and
  `/v3/documents/processing`; `errorCode`/`errorMessage` on processing items; `containerTags`
  query on `/v3/container-tags/list`; a typed 409 body on `/v3/settings/reset`. The rest is
  nullable-type normalization.
- Unchanged limits: batch `documents` 1–600; bulk delete `ids` 1–100; v4 direct create 1–100
  memories (≤10,000 chars each); v4 `searchMode` default `memories`.

### v5 path inventory (22)

`/connectors`, `/feedback`, `/namespaces`, `/ns`, `/ns/{namespace}`,
`/ns/{namespace}/connectors`, `/ns/{namespace}/connectors/{id}`, `/ns/{namespace}/connectors/{id}/sync`,
`/ns/{namespace}/document`, `/ns/{namespace}/document/batch`, `/ns/{namespace}/document/file`,
`/ns/{namespace}/document/file/{id}`, `/ns/{namespace}/document/{id}`,
`/ns/{namespace}/list/documents/memory-counts`, `/ns/{namespace}/list/{type}`,
`/ns/{namespace}/memories`, `/ns/{namespace}/memories/semantic`, `/ns/{namespace}/memories/{id}`,
`/ns/{namespace}/profile`, `/ns/{namespace}/profile/buckets`, `/ns/{namespace}/search`, `/organization`.

The v5 connector `provider` enum contains `github`, `gmail`, `google-drive`, `granola`,
`notion`, `onedrive`, `s3`, and `web-crawler`. That is the same eight as July.

## Live probe: `experiments/run_v5_contract_refresh.py`

Run `v5refresh-20261105145252-12f239`, namespace `lab:v5refresh:20261105145252-12f239`.

| Step | Status |
|---|---|
| v5 add document, search (default + memories), profile, list | 401 Unauthorized |
| legacy v4 search, v4 direct memory create | 401 Unauthorized |
| v5 semantic forget dry-run | 401 Unauthorized |
| cleanup: delete document, delete namespace, verify absent | 401 Unauthorized |

The workspace key was present and well-formed (prefix `sm_`, no whitespace or quoting). It
was rejected on every route, both legacy and v5. Conclusion: **credential invalid for this
account**, not an API failure. Because every write was rejected, nothing was created, and no
residual resources need cleanup. All behavioral questions listed in the delta note remain
**unverified**.

Not attempted by design: `/feedback` (it would page Supermemory staff), scoped-key minting or
revocation, organization settings, connectors, Router (needs an OpenRouter key and a positive
Supermemory key), and the Local upgrade drill (needs a disposable host).
