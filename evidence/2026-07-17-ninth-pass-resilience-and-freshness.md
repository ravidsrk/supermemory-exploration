# Ninth-pass resilience, freshness, and operations evidence — 2026-07-17

## Research question

Which still-unproven Supermemory surfaces and cross-provider workflows can become distinct,
production-shaped agents—and what live evidence would falsify their safety or usefulness?

## Executive summary

Five new implementations and five final hosted experiments passed. The field lab now contains
52 reference implementations and 238 package-aware offline tests.

| Agent | Capability under test | Final secret-safe run | Result |
|---|---|---|---|
| Source-revision citation guardian | Exact current chunks, revision staleness, signed answer persistence | `citation-guardian-20260717025046-7a0955` | Passed |
| Profile-schema evolution steward | AI bucket suggestions, additive schema control, drift/replay denial | `profile-schema-20260717025939-968417` | Passed |
| Risk-aware continuity gateway | Signed stale cache, risk classes, circuit breaker, restart recovery | `continuity-gateway-20260717030403-95d81c` | Passed |
| Adaptive bulk-ingestion controller | `429` backpressure, checkpoint resume, processing readiness, reconciliation | `adaptive-bulk-20260717030715-05c68f` | Passed |
| Memory SLO canary monitor | Profile/memories/hybrid/documents correctness, latency, tenant-leak alerting | `memory-slo-20260717031011-538c84` | Passed |

The practical conclusion is that a memory layer needs its own reliability and change-control
plane. Retrieval quality alone is insufficient. A production agent needs to know which source
revision it cited, whether a profile schema changed concurrently, whether remembered context
is live or stale, whether a bulk acknowledgement has finished processing, and whether every
read surface is still returning the correct tenant's canary.

## Current product, source, GitHub, research, and X recheck

The public monorepo was re-inspected at
[`82c03a87ce1e89302b915e55739c9482209e0408`](https://github.com/supermemoryai/supermemory/tree/82c03a87ce1e89302b915e55739c9482209e0408).
The two commits after the prior `8d92633` pin changed the README and coding-plugin docs, not
the API validation surface. One removed a Pro-plan banner from Claude Code/OpenCode guidance;
the other foregrounded current vendor research numbers. The hosted OpenAPI still exposed 32
paths in this recheck.

The official [research page](https://supermemory.ai/research/) and current README claim 95%
Recall@15 on 500 LongMemEval questions at about 720 context tokens, a 99.4% context reduction,
and lower token use for SMFS on the xAFS benchmark. These are vendor-published benchmark
results. This pass did not reproduce them and does not mix them with the lab's 12-sample SLO
run.

Underused but material current API surfaces include:

- `GET /v3/documents/processing`, which returns processing documents and `totalCount`;
- `POST /v3/settings/suggest-buckets`, whose observed response contained five bounded
  `{key, description}` suggestions;
- profile-bucket replacement on a container, with effective organization buckets remaining
  outside the container's removal authority;
- connection resource discovery and exact configuration through the official
  [resource](https://supermemory.ai/docs/api-reference/connections/fetch-resources) and
  [configuration](https://supermemory.ai/docs/api-reference/connections/configure-connection)
  operations;
- the documented 1–600 document batch boundary, singular batch `containerTag`, flat metadata,
  and separate document-processing state in the current
  [OpenAPI](https://api.supermemory.ai/v3/openapi).

The GitHub API returned 26 open issue records in the point-in-time audit. They remain reported,
not reproduced. Operationally relevant examples are the macOS self-host wedge
[#1296](https://github.com/supermemoryai/supermemory/issues/1296), profile migration
[#1293](https://github.com/supermemoryai/supermemory/issues/1293), middleware outage behavior
[#1287](https://github.com/supermemoryai/supermemory/issues/1287), Python SDK dedup parsing
[#1266](https://github.com/supermemoryai/supermemory/issues/1266), integration drift
[#1247](https://github.com/supermemoryai/supermemory/issues/1247), and MCP scoping
[#1246](https://github.com/supermemoryai/supermemory/issues/1246).

A fresh ScrapeCreators read of the official public X feed returned nine bounded records. Recent
signals included a local voice agent using memories
([official repost](https://x.com/supermemory/status/2077838827302125582)), a Tesla-assistant
hackathon build ([official post](https://x.com/supermemory/status/2077488434026012774)), and a
personalized tweet-writer example
([official repost](https://x.com/supermemory/status/2076637279628730771)). The account also
continues to position the local runtime as a self-contained agent memory layer
([launch post](https://x.com/supermemory/status/2064749494412222583)). These are useful product
and use-case signals, not reliability, privacy, or benchmark evidence.

## 1. Source-revision citation guardian

Implementation:
[`citation_guardian.py`](../src/supermemory_lab/citation_guardian.py) and
[`run_source_revision_citation_guardian.py`](../experiments/run_source_revision_citation_guardian.py).

The guardian reads ordered current chunks for one exact document and signs:

- document and application-owned revision IDs;
- ordered chunk IDs, positions, and content hashes;
- a complete source digest;
- effective and expiry times;
- required and forbidden source terms.

The model supplies prose and exact quote candidates only. Trusted code verifies that every
quote occurs in the cited current chunk, that answer/source terms match the revision contract,
and that the source digest is unchanged immediately before persistence. An exact external
authorization binds snapshot hash to report hash, and a replay ledger permits one write.

The live run ingested revision V1, produced a one-chunk exact citation, replaced the source with
V2, and observed V2 after four chunk polls. The V1 snapshot could no longer persist. The V2
answer cited the current chunk, contained the current window, excluded the old window and a
planted instruction, denied wrong authorization and replay, persisted one reviewed answer, and
found V2 but not the exact old revision in a fresh source search. Both isolated containers were
deleted.

The first attempt failed safely before any durable answer. It had allowed the model to emit the
revision ID, and the model returned a non-canonical value. The final interface makes revision
identity application-owned. This is an important general rule: models may explain source
content, but source identity and freshness must come from trusted state.

## 2. Governed profile-schema evolution steward

Implementation:
[`profile_schema_steward.py`](../src/supermemory_lab/profile_schema_steward.py) and
[`run_profile_schema_evolution_steward.py`](../experiments/run_profile_schema_evolution_steward.py).

The steward validates generated bucket keys against the current lowercase key pattern and
length limits, captures the container-owned and effective schemas separately, and signs their
hashes. Plans are additive only. They cannot collide with effective organization keys, mutate
or remove existing container buckets, exceed the 50-bucket cap, or apply after concurrent
schema drift. Exact authorization and replay denial protect the final update.

The hosted suggestion call returned five structurally valid suggestions and took 25.4 seconds
in this single run. One was adopted alongside a required lab bucket. A concurrent external
bucket addition invalidated the first plan. After recapture, the refreshed plan preserved the
initial and concurrent buckets, added the required bucket, applied the exact expected schema,
and routed a new marker into the selected profile without exposing the other tenant. Wrong
authorization and replay were denied; cleanup passed.

AI suggestion is therefore a schema-design input, not schema authority. It should run in an
administrative workflow with review, not on the critical path of an agent turn.

## 3. Risk-aware memory-outage continuity gateway

Implementation:
[`continuity_gateway.py`](../src/supermemory_lab/continuity_gateway.py) and
[`run_memory_outage_continuity_gateway.py`](../experiments/run_memory_outage_continuity_gateway.py).

The gateway atomically composes profile and hybrid search into a bounded, signed
last-known-good snapshot. Cache use requires:

- an intact signature and unexpired snapshot;
- the exact container and query class;
- explicit stale permission;
- a non-high-risk request.

Two consecutive failures open a 30-second circuit. Standard/low-risk calls can receive an
application-owned `MEMORY_STATUS=...` stale banner; high-risk calls receive deterministic
`MEMORY_UNAVAILABLE` and skip the model. Open-circuit calls skip the backend. A half-open probe
after cooldown can close the circuit. Model prose has no external-action authority, and output
containing configured forbidden memory instructions is withheld.

The live drill first produced a fresh signed answer. An injected backend failure yielded an
explicit stale answer with the correct canary and no planted instruction. A high-risk request
failed closed without an LLM call and opened the circuit. The next request used the cache with
no backend call; a different query class could not reuse it. A fresh process loaded the valid
snapshot, a tampered copy was denied, and a half-open live probe recovered. The other tenant
was absent and cleanup passed.

This was an injected client-side outage over a real hosted baseline, not a Supermemory service
incident. It proves policy behavior under failure, not hosted availability.

## 4. Adaptive bulk-ingestion controller

Implementation:
[`bulk_ingestion_controller.py`](../src/supermemory_lab/bulk_ingestion_controller.py) and
[`run_adaptive_bulk_ingestion_controller.py`](../experiments/run_adaptive_bulk_ingestion_controller.py).

The deterministic controller signs a manifest of stable custom IDs, source hashes, and
metadata. It uses additive-increase/multiplicative-decrease batch sizing, honors bounded
`Retry-After`, halves oversized batches, refuses partial acknowledgements, and emits a signed
checkpoint after every accepted batch. A fresh process verifies that checkpoint and submits
only pending stable IDs. Completion requires target-side custom-ID/hash reconciliation plus
exit from the processing queue; acceptance alone is never semantic readiness.

The live run placed 24 SuperRAG records behind one injected `429` with `Retry-After: 2`. Batch
attempt sizes were `[8, 4, 5, 6, 7, 2]`: eight was throttled, four succeeded, and subsequent
successes increased the target. The controller intentionally paused after two accepted
batches with 9/24 records and a signed incomplete checkpoint. A fresh controller resumed to
24 unique response IDs.

The immediate inventory was exact, but only 8 documents were done while 16 were still
processing. A later barrier found 24/24 done, zero processing, zero failed, exact hashes, and
both edge markers searchable. This is direct live evidence that accepted, inventoried, and
semantically ready are three different states. The `429` itself was injected; the subsequent
five batches and processing observations were hosted. Cleanup deleted all 24 records and the
negative-control tenant.

## 5. Four-surface memory SLO canary monitor

Implementation:
[`memory_slo_monitor.py`](../src/supermemory_lab/memory_slo_monitor.py) and
[`run_memory_slo_canary_monitor.py`](../experiments/run_memory_slo_canary_monitor.py).

The monitor sends exact canaries through v4 memories, v4 hybrid, v3 documents, and v4 profile.
Every sample records expected-hit, forbidden-marker leak, result count, error type, and client
latency. The aggregate and per-surface metrics are signed. A healthy report is deterministic
and makes no model call. An unhealthy report sends only aggregate metrics and error types to
the LLM; raw memory never enters the alert explanation, which remains inside a
`NO_EXTERNAL_ACTION` envelope.

Three hosted rounds produced 12/12 successful probes and zero tenant leaks. Client-observed
latency was 806 ms p50 and 1.31 s p95 overall. Per-surface p95 was 887 ms for documents, 839 ms
for hybrid, 1.19 s for memories, and 1.31 s for profile. The sample is tiny and sequential;
these are regression anchors, not SLA estimates.

A separate wrapper injected one forbidden result without reading the other tenant. The signed
alert detected one leak, reduced success to zero, invoked OpenRouter once with metrics only,
excluded the raw marker, and authorized no action. Healthy operation invoked OpenRouter zero
times. Both hosted containers were deleted.

The observed profile p95 is not a valid refutation of the vendor's roughly 50 ms profile
positioning: the lab measured client wall time from one region with query-specific profile
work, network overhead, and only three samples. The mismatch is exactly why production owners
should measure their own SLO instead of copying a benchmark headline.

## Cross-agent architecture

```text
source revision ──> citation guardian ──> exact cited answer
       │                     │
       └── current digest ───┘

profile schema suggestion ──> additive steward ──> reviewed schema

bulk manifest ──> adaptive submit ──> signed checkpoint ──> processing barrier
                                                           │
                                                           └── exact inventory

live read ──> continuity gateway ──> fresh / stale / unavailable banner
                    │
                    └── signed last-known-good cache + circuit breaker

all read surfaces ──> SLO canaries ──> signed health/violation report
```

The common pattern is deterministic control around probabilistic memory. Signatures do not
make content true; they make ancestry, scope, and tampering testable. Exact canaries do not
prove broad recall quality; they make silent breakage visible. Stale cache does not make an
outage healthy; it gives low-risk agents a labeled continuity mode.

## Contradictions, limitations, and open gaps

1. **Vendor benchmark claims are not reproduced here.** The official 95% Recall@15 and token
   numbers remain primary vendor research, not lab observations.
2. **The SLO run is intentionally small.** Twelve sequential samples cannot estimate tails,
   concurrency behavior, regional variance, or an SLA.
3. **The outage was injected.** Circuit and cache policy passed over real prior memory, but no
   provider outage occurred.
4. **The rate limit was injected.** Backpressure and resume logic passed; hosted rate limits at
   sustained batch load were not challenged.
5. **Twenty-four is not six hundred.** The current documented batch ceiling, large payloads,
   and 100-ID bulk-delete boundary still need isolated boundary tests.
6. **Source freshness covered one update.** Concurrent writers, delete/recreate, multi-document
   answers, chunk reordering, and long citation chains remain untested.
7. **Profile schema was container-owned.** Organization-bucket creation/removal, permissions,
   and migration across existing tenants remain outside this isolated run.
8. **AI suggestion latency was one sample.** The 25.4-second call supports asynchronous admin
   use, not a general performance conclusion.
9. **Connector resources were source-inspected, not entitled/live-tested.** GitHub resource
   discovery/configuration/import remains a priority on a qualifying plan.
10. **X posts are demos and positioning.** A public voice/Tesla/writer build does not establish
    data governance, scale, or support quality.
11. **Issue reports are reports.** They generate targeted regression cases but are not treated
    as reproduced defects.
12. **Hosted extraction/search internals remain opaque.** The MIT repository exposes extensive
    clients, validation, docs, apps, and integrations, not the complete hosted engine.

## Six-month operating recommendations

1. Run the four-surface canary monitor every 5–15 minutes in a dedicated synthetic container;
   alert immediately on any forbidden marker and separately on latency/miss budget burn.
2. Put the continuity gateway around user-facing recall. Permit stale context only by explicit
   query class and risk level; never for authorization, money, deployment, deletion, health,
   or other high-consequence decisions.
3. Make source revision and chunk quote mandatory for policies, contracts, incident runbooks,
   and other mutable knowledge. Recheck the source digest immediately before durable use.
4. Manage profile buckets as versioned schema. Review AI suggestions offline, use additive
   plans, detect drift, and retain a rollback/migration plan outside memory.
5. Use stable custom IDs and hashes for every bulk load. Persist checkpoints externally,
   honor `Retry-After`, poll the processing endpoint, and reconcile the target before declaring
   readiness or deleting the source.
6. Keep the intake firewall, exact authorization, replay ledger, legal holds, action
   permission, and external audit in deterministic state. None should be inferred from memory.
7. Pin and retest the 32-path OpenAPI, integration defaults, processing wire shape, and current
   monorepo commit monthly.
8. Next run 100+ blinded domain questions, concurrent SLO load, hosted throttling, connector
   lifecycle on an entitled plan, self-host upgrade/restore, and exact cardinality/file limits.

## Verification

```text
PYTHONPATH=src python3 -m unittest discover -v
Ran 238 tests ... OK

Final live evaluations: 5/5 passed
Final live cleanup: 10/10 isolated containers deleted successfully
Reference implementations: 52
Hosted OpenAPI paths rechecked: 32
```

Raw traces remain ignored under `.runs/`. This note contains no credentials, authorization
headers, temporary file URLs, raw profile suggestions, or customer data.
