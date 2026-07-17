# Tenth-pass capacity, connectors, evaluation, and recovery evidence — 2026-07-17

## Research question

Which remaining unproven boundaries—connector lifecycle, maximum-cardinality ingestion and
deletion, concurrent recall, a larger blinded evaluation, and self-host recovery—can be closed
with safe live evidence, and which require external entitlement or user OAuth?

## Executive answer

Four boundaries closed positively and one closed as a precise entitlement boundary. The lab
now contains 57 reference implementations and 262 package-aware offline tests.

| Track | Final secret-safe run | Result |
|---|---|---|
| Governed connector onboarding | `connector-onboarding-20260717033031-60e896` | Correctly blocked before OAuth by hosted `403`; no connection or document was created |
| Maximum-cardinality ingest/delete | `max-cardinality-20260717033818-2d08ea` | Exactly 600 accepted, processed, reconciled, and deleted in six exact 100-ID batches |
| Concurrent four-surface recall | `concurrent-recall-20260717034325-aafc34` | 20/20 sequential and 20/20 concurrent probes correct, with zero errors or tenant leaks |
| Blinded 100-case domain benchmark | `blinded-domain-100-20260717035326-ecb9ea` | Retrieval 100/100; memory answers 100/100; no-memory controls 10/100; zero leaks/bypasses |
| Stopped-state self-host recovery | `self-host-recovery-20260717041842-8d4a8f` | Byte-identical backup/restore and recall passed; production gate remained HOLD |

The practical conclusion is not “every surface is production-ready.” Hosted direct APIs now
have strong synthetic evidence at their documented cardinality boundary and under bounded
read concurrency. Connector code can govern a lifecycle safely, but this account cannot cross
the plan entitlement and user-OAuth boundary. Local state can be backed up and restored, but
the reproduced signal-5 shutdown, detached worker, queued-ingestion wedge, and lack of a newer
upgrade target make self-hosting a production HOLD on this macOS setup.

## Sources and point-in-time state

- The hosted [OpenAPI](https://api.supermemory.ai/v3/openapi) exposed 32 paths. Its batch-add
  schema accepts 1–600 documents and exact bulk delete accepts 1–100 IDs.
- The official [connector overview](https://supermemory.ai/docs/connectors/overview) and hosted
  schema exposed Notion, Google Drive, OneDrive, Gmail, GitHub, web crawler, S3, and Granola.
  The [resource lifecycle](https://supermemory.ai/docs/memory-api/connectors/managing-resources)
  was documented for GitHub only.
- The official [connection creation](https://supermemory.ai/docs/api-reference/connections/create-connection),
  [resource fetch](https://supermemory.ai/docs/api-reference/connections/fetch-resources),
  [configuration](https://supermemory.ai/docs/api-reference/connections/configure-connection),
  and [sync](https://supermemory.ai/docs/api-reference/connections/sync-connection) operations
  informed the governed state machine.
- The official [self-host overview](https://supermemory.ai/docs/self-hosting/overview),
  [quickstart](https://supermemory.ai/docs/self-hosting/quickstart), and
  [configuration](https://supermemory.ai/docs/self-hosting/configuration) place local state,
  auth, and model cache in `SUPERMEMORY_DATA_DIR`; provider configuration remains separate.
- The current [local changelog](https://supermemory.ai/changelog/local/) described the upgrade
  command. GitHub release `server-v0.0.5` was still the newest published version, so there was
  no newer release for a genuine version-to-version rehearsal.
- Source inspection remained pinned to
  [`82c03a87ce1e89302b915e55739c9482209e0408`](https://github.com/supermemoryai/supermemory/tree/82c03a87ce1e89302b915e55739c9482209e0408).
  Source and hosted connector types were not treated as interchangeable where they differed.
- A point-in-time GitHub audit found 26 open issue records excluding pull requests. Relevant
  reports included macOS self-host behavior
  [#1296](https://github.com/supermemoryai/supermemory/issues/1296), profile migration
  [#1293](https://github.com/supermemoryai/supermemory/issues/1293), middleware outage
  [#1287](https://github.com/supermemoryai/supermemory/issues/1287), Python result shape
  [#1266](https://github.com/supermemoryai/supermemory/issues/1266), integration drift
  [#1247](https://github.com/supermemoryai/supermemory/issues/1247), and MCP scoping
  [#1246](https://github.com/supermemoryai/supermemory/issues/1246). Issue titles are reported
  risk signals, not reproduced root causes.

## 1. Governed connector onboarding

Implementation:
[`connector_onboarding_governor.py`](../src/supermemory_lab/connector_onboarding_governor.py)
and
[`run_governed_connector_onboarding.py`](../experiments/run_governed_connector_onboarding.py).

The governor signs provider, container, document limit, metadata, redirect target, and resource
policy before any hosted mutation. It stores only the OAuth-link hash/presence, never the link
itself. GitHub resource selection requires a second signed intent after re-fetching resources;
provider, connection, or resource drift fails closed. Wrong authorization and replay are
denied before the API call. Disconnect explicitly preserves synchronized documents unless a
separate deletion authorization exists.

The final live run reached the current account boundary exactly: connection creation returned
`403`, state became `plan-or-entitlement-blocked`, and no connection, OAuth URL, resource
selection, sync, or document existed. Cleanup received the typed already-absent result. This is
a successful negative-control run, not a connector-lifecycle success. Completing OAuth and
resource/update/revocation tests requires both connector entitlement and a consenting user.

Google Drive deserves a special guardrail: the default selected/picker scope is narrower,
whereas `metadata.syncScope=full` broadens ingestion to the whole Drive. The broad mode should
require an explicit, separately reviewed intent.

## 2. Exact maximum-cardinality ingestion and deletion

Implementation:
[`bulk_ingestion_controller.py`](../src/supermemory_lab/bulk_ingestion_controller.py),
[`exact_deletion_controller.py`](../src/supermemory_lab/exact_deletion_controller.py), and
[`run_max_cardinality_capacity_audit.py`](../experiments/run_max_cardinality_capacity_audit.py).

The controller locally denied a 601-document write and a 101-ID delete. It then submitted
exactly 600 stable IDs and source hashes in one hosted request. Immediate inventory contained
all 600 records while 78 were still processing. A bounded barrier reached 600/600 `done`, and
first/middle/last canaries were searchable.

Deletion required a signed exact-ID manifest and external authorization. Wrong authorization
was denied. The run intentionally paused after two 100-ID batches, loaded the checkpoint in a
fresh controller, and deleted the remaining 400. Six exact batches removed all records; replay
of the completed checkpoint was idempotent. Exact inventory and negative search were empty,
and no broad selector was used for primary cleanup.

An earlier run is operationally important. The 600-record POST exceeded a 60-second client
timeout, acknowledgement was unknown, and later inventory was empty. It also exposed an empty
container-delete `500`; one scoped teardown canary made the isolated container deletable. The
client now types timeouts, and ambiguous write recovery relies only on exact provider inventory
matching run ID, stable ID, and source hash—never blind POST retry. Partial ambiguity fails
closed. The successful final run used a 240-second timeout.

The schema maximum is not a throughput recommendation. The official general ingestion guide
recommends smaller paced groups; production loaders should tune below 600, use stable IDs,
checkpoint every acknowledgement, and distinguish accepted, inventoried, processing, and
searchable states.

## 3. Concurrent four-surface recall challenge

Implementation:
[`concurrent_recall_challenger.py`](../src/supermemory_lab/concurrent_recall_challenger.py)
and
[`run_concurrent_four_surface_recall_challenge.py`](../experiments/run_concurrent_four_surface_recall_challenge.py).

The challenger signs its input and report, caps workers and requests, grants no write or model
authority, and records correctness, leaks, errors, and per-surface latency. Five rounds across
profile, memories, hybrid, and documents produced 20 sequential and 20 concurrent requests.

| Metric | Sequential | Concurrent (8 workers) |
|---|---:|---:|
| Correct probes | 20/20 | 20/20 |
| Errors / tenant leaks | 0 / 0 | 0 / 0 |
| Wall time | 13,870.373 ms | 2,147.680 ms |
| Throughput | 1.442 req/s | 9.312 req/s |

Concurrent p95 was 586.0 ms for documents, 1,433.2 ms for hybrid, 1,075.4 ms for memories,
and 1,272.2 ms for profile. Peak in-flight work was eight. This is a useful bounded regression
and demonstrates that all four surfaces remained correct through one shared client. It is not
a load test, regional SLA, or sustained-capacity claim.

## 4. Blinded 100-case domain benchmark

Implementation:
[`blinded_domain_benchmark.py`](../src/supermemory_lab/blinded_domain_benchmark.py),
[`run_blinded_domain_100_benchmark.py`](../experiments/run_blinded_domain_100_benchmark.py),
and [`domain-100-case.schema.json`](../benchmarks/domain-100-case.schema.json).

The signed manifest allocates exactly 100 synthetic cases: 10 stable-personal, 10 recent,
15 knowledge-update, 10 temporal, 10 multi-hop, 10 source-verbatim/citation, 10 distractor,
10 forget/correction, 10 tenant-negative, and 5 prompt-injection. The deterministic term
rubric is hidden from the answer prompt. Memory-first and baseline-first order is
counterbalanced, retrieval and answer scores remain separate, and concurrency is capped at
eight. The model has no write or action authority.

Final results:

| Metric | Result |
|---|---:|
| Retrieval evidence | 100/100 |
| Memory-assisted answers | 100/100 |
| No-memory answers | 10/100 |
| Lift | +90 percentage points |
| Case errors / tenant leaks / injection bypasses | 0 / 0 / 0 |
| Search p50 / p95 | 671.4 / 1,017.8 ms |
| Answer p50 / p95 | 1,246.7 / 2,203.5 ms |
| Mean estimated context | 374.1 tokens |
| Maximum rendered context | 1,926 characters |
| Order | 57 baseline-first / 43 memory-first |

The ten baseline passes were expected `UNKNOWN` tenant-negative controls. A first full run
failed honestly: all ten recent cases missed because a verbose natural query was insufficiently
selective in the 100-record corpus, and all ten citation answers failed because the shared
renderer ignored nested v3 document chunks. The fix separated application-owned retrieval
queries from user questions and rendered nested chunks. The hidden scoring rubric did not
change. A focused live probe also confirmed the recent marker was available; the defect was
retrieval construction, not missing write visibility.

This is a synthetic domain regression, not the public MemoryBench dataset and not an official
vendor score. The rubric is deterministic rather than a model judge. It is strong evidence
for this bounded corpus and implementation, not a general 100% production-accuracy claim.

## 5. Stopped backup, restart, and clean restore

Implementation:
[`self_host_recovery.py`](../src/supermemory_lab/self_host_recovery.py) and
[`run_self_host_backup_restore.py`](../experiments/run_self_host_backup_restore.py).

Using checksum-verified server v0.0.5 and a disposable data directory, the final drill wrote a
direct v4 static-memory canary, stopped the server, copied the data tree, and compared complete
manifests. The source and backup matched. Same-directory restart preserved search and profile.
A byte-identical clean-directory restore on a second port also preserved search and profile,
then exact deletion was verified in both restored and source copies. The source tree contained
51 files and 378,216,164 bytes. Provider configuration was restored separately and was never
treated as part of the data backup.

The durability result passed, but production readiness did not:

- every Bun parent exited with signal-derived code `-5` instead of a clean shutdown;
- four detached worker processes required explicit detection and reaping;
- an earlier v3 document canary stayed queued for 180 seconds with no workflow start;
- the earlier shutdown emitted a Bun C++ panic;
- installed and newest published versions were both 0.0.5, so no newer-version upgrade
  rehearsal was possible.

The final script resolves macOS `/tmp` and `/private/tmp` aliases when locating worker command
lines; without that, orphan detection could miss workers. All temporary copies, local API
keys, server logs, workers, and listeners were removed. The safe interpretation is: direct
memory state survived a stopped snapshot, restart, and clean restore, while this platform and
release remain a production HOLD pending clean shutdown, queue recovery, explicit worker
supervision, and a real version upgrade.

## Architecture and practical agent consequences

```text
connector intent ──> entitlement ──> user OAuth ──> selected resources ──> sync/revoke
       │                 │
       └── signed policy └── typed external boundary

stable ingest manifest ──> bounded POST ──> exact inventory ──> processing ──> recall
          │                    │
          └── checkpoint/hash ─┴── ambiguous-write reconciliation

four read surfaces ──> bounded concurrency ──> correctness/leak/latency report

blinded cases ──> trusted retrieval query ──> bounded context ──> model answer
      │                                                     │
      └── hidden deterministic rubric ──────────────────────┘

stopped data tree ──> complete manifest ──> backup ──> clean restore
provider env ────────────────────────────────────────> separate restore
```

These primitives enable production-shaped agents such as a connector admission controller,
large migration worker, exact rollback service, cross-surface SLO challenger, release-gated
domain evaluator, and local-memory disaster-recovery operator. In every case, Supermemory is
the context plane; trusted application code owns identity, authorization, checkpoints,
evaluation, cleanup, and operational gates.

## Limitations and remaining external work

1. Connector OAuth, selected-resource update, resync, revoke, and ACL-change behavior remain
   unobserved because the current account is not entitled and no user completed OAuth.
2. The 600-record run is a single synthetic batch, not sustained throughput or cost evidence.
3. The concurrent challenge is 40 requests with eight workers, not a soak or write-contention
   test.
4. The 100-case corpus is synthetic and its rubric deterministic. Run product-specific human
   review and a public benchmark before comparing vendors.
5. Self-host recovery covered direct-memory state. The queued v3 ingestion failure must be
   resolved and retested; a real upgrade awaits a release newer than 0.0.5.
6. Current X posts about voice, vehicle, and personalized-writing agents remain product-direction
   signals, not operational or safety evidence.

## Cleanup and security

Raw traces and generated result artifacts remain ignored under `.runs/`. No authorization
header, environment variable, OAuth link, local API key, or customer content is committed.
Every hosted container created by the final runs was deleted or verified absent. The local
servers, generated keys, logs, workers, listeners, source/backup/restore directories, and
other disposable artifacts were removed. Credentials pasted into any chat or other untrusted
surface should still be rotated independently of repository cleanliness.
