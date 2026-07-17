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

## Second-pass practical agents and evaluations

```bash
PYTHONPATH=src python3 experiments/run_consistency_matrix.py
PYTHONPATH=src python3 experiments/run_query_sensitivity.py
PYTHONPATH=src python3 experiments/run_change_monitor.py
PYTHONPATH=src python3 experiments/run_safe_tool_execution.py
PYTHONPATH=src python3 experiments/run_governance_scorecard.py
PYTHONPATH=src python3 experiments/run_signal_radar.py
PYTHONPATH=src python3 experiments/run_retrieval_policy_grid.py
PYTHONPATH=src python3 experiments/run_release_triage_rehearsal.py
```

These are live, synthetic, and scoped to unique `lab:` containers. Together they add:

- exact-canary visibility separated from natural-query relevance;
- a reversible Context.dev monitor lifecycle with quota returning to zero;
- one price-capped Monid GET and one no-auth Composio read;
- 15 update/forget/isolation/injection cases;
- fresh multi-source radar plus a memory-only fallback;
- 120 retrieval-policy combinations and an agent-level verification;
- Vercel observation plus a test-guided, egress-blocked repair loop.

The corrected results and failed first attempts are in
[second-pass evidence](../evidence/2026-07-16-second-pass-agents.md). Do not skip the failures:
the long HN query returned zero results, an untuned agent query missed at the winning threshold,
and the first webhook patch accepted future timestamps. Each caused a code or query-policy
change before the final passing trace.

## Third-pass lifecycle, Router, and benchmark experiments

```bash
PYTHONPATH=src python3 experiments/run_evolving_preference_agent.py
PYTHONPATH=src python3 experiments/run_filter_erasure_agent.py
PYTHONPATH=src python3 experiments/run_lifecycle_agents.py
PYTHONPATH=src python3 experiments/run_router_continuity_matrix.py
PYTHONPATH=src python3 experiments/run_domain_memory_benchmark.py
```

These scripts add exact-canary consistency barriers, container settings/custom buckets,
conversation-plus-normalized-fact personalization, preview-gated semantic erasure, seven
filter shapes, memory expiry/cancellation, queued container merge, Router continuity modes,
and a matched memory/no-memory domain QA gate.

Final observed outcomes:

- corrected preference versioning, custom bucket, replay idempotency, isolation, and cleanup
  passed; the completed conversation did not automatically yield the expected preference in
  the 30-second window;
- all seven v4 search filter cases passed and one-target semantic erasure retained its control;
  filtered memory listing and explicit-forget audit recovery did not behave as expected;
- expiry hid a lease after about 15.4 seconds, cancellation preserved version 2, and the
  expired memory was recoverable through the forgotten include path;
- merge reached `completed`, moved source data, removed the source, and retained target data
  and settings; target search worked earlier at `cleanup_pending`;
- Router delta continuation passed 3/3 and direct API pool memory worked with/without a
  conversation header, but Router-generated new-conversation recall failed;
- the domain smoke suite scored 12/12 with memory and 2/12 without, with zero leaks/bypasses,
  659.3 ms search p50, 1,143.3 ms p95, and about 327 estimated context tokens.

See the curated
[third-pass evidence](../evidence/2026-07-16-third-pass-lifecycle-and-benchmark.md) for run IDs,
failed rehearsals, contradictions, and operating rules.

## Fourth-pass memory-native agent systems

```bash
PYTHONPATH=src python3 experiments/run_enterprise_context_agent.py
PYTHONPATH=src python3 experiments/run_corroborated_research_swarm.py
PYTHONPATH=src python3 experiments/run_adaptive_model_router.py
PYTHONPATH=src python3 experiments/run_temporal_agenda_agent.py
PYTHONPATH=src python3 experiments/run_dependency_risk_guardian.py
```

Final observed outcomes:

- a three-container scoped key read organization/project/user context, received `403` for
  another tenant and `401` after revocation, while application action authority stayed false;
- the research swarm promoted only after official plus multi-channel fresh support, resisted a
  retrieved poison memory, and refused promotion in memory-only mode;
- a persisted model calibration winner failed a related output contract, fell back correctly,
  wrote the failure, and was avoided by the next process;
- natural-time retrieval passed 10/10 exact, relative, future, and negative controls at 923.9 ms
  client-wall p50 and 1,186.9 ms p95;
- the dependency guardian tested the actual installed version with Monid, Exa, Composio, and an
  egress-blocked SuperServe sandbox, but kept production authorization false;
- the current Context.dev Markdown GET contract was verified after the older POST shape returned
  `403`.

See the [fourth-pass evidence](../evidence/2026-07-16-fourth-pass-agent-systems.md) for exact run
IDs, model calibration numbers, first failures, caveats, and cleanup.

## Fifth-pass operational agent systems

```bash
PYTHONPATH=src python3 experiments/run_governed_memory_curator.py
PYTHONPATH=src python3 experiments/run_resumable_agent_workcell.py
PYTHONPATH=src python3 experiments/run_relationship_account_briefing.py
PYTHONPATH=src python3 experiments/run_incident_forensics_agent.py
PYTHONPATH=src python3 experiments/run_tool_economics_portfolio.py
```

Final observed outcomes:

- the curator quarantined retrieved poison, denied a wrong approval hash and replay, applied one
  versioned correction, and verified latest truth plus response parent/root lineage;
- the signed workcell ignored a forged checkpoint, rejected invalid output, resumed three stages
  across fresh processes, deduplicated an acknowledgement-loss retry, and denied a backward
  transition;
- batch ingestion accepted 3/3 relationship documents, but repeated Dynamic Dreaming checks did
  not reach exact fact readiness in the bounded 60–90 second windows; confirmed direct-fact
  fallback enabled the four-provider cited brief while outreach stayed false;
- incident forensics observed only bounded Vercel counts, falsified retry hypotheses in an
  egress-blocked sandbox, persisted a verified lesson, and kept production root cause unknown;
- all Monid, Composio, and Exa read routes returned valid Hacker News results; Exa and Monid had
  comparable dated costs, while unknown Composio cost stayed shadow-only;
- every final evaluation passed, cleanup succeeded or found the empty control already absent,
  and the complete offline suite passed 110 tests.

The failed rehearsals were useful: superseded v1 was not a separate top-level current entry
(the sixth pass later found it in nested history); a scorer
initially conflated semantic discovery with an exact serialized barrier; Dynamic Dreaming
remained pending despite completed documents; and opaque citation IDs were not reliable until
the prompt required them. See the
[fifth-pass evidence](../evidence/2026-07-16-fifth-pass-operational-agents.md) for run IDs,
timings, implementation boundaries, and primary sources.

## Sixth-pass deep agent systems

```bash
PYTHONPATH=src python3 experiments/run_graph_review_steward.py
PYTHONPATH=src python3 experiments/run_decision_council.py
PYTHONPATH=src python3 experiments/run_adaptive_tutor.py
PYTHONPATH=src python3 experiments/run_due_diligence_campaign.py
PYTHONPATH=src python3 experiments/run_change_risk_board.py
PYTHONPATH=src python3 experiments/run_retention_controller.py
```

Final observed outcomes:

- the latest v3 lineage entry contained nested history `[1, 2, 3]` with a valid parent/root
  chain; ordinary-memory inferred review returned 409, while the bounded seed produced no real
  candidate;
- three model families returned evidence-bound `STAGED` votes, retrieved poison was excluded,
  the result remained a non-authoritative proposal, and a changed evidence digest made it
  stale;
- the tutor ignored unsigned mastery poison, selected a decayed lesson, accepted only an
  egress-blocked verified 4/4 grade, created mastery version 2, and recovered it in a fresh
  process;
- due diligence resumed from a signed checkpoint, cited three publishers, represented known
  and unknown costs, exposed Exa/Monid/Composio 401s, labeled the report `degraded-partial`,
  and withheld conclusion promotion and purchase authority;
- a 5/5 staged-rollout rehearsal could not override unhealthy live counts; the board returned
  `HOLD`, persisted no project names, and kept deployment authority false;
- legal-hold versioning invalidated an old deletion plan; wrong hold/plan approvals and replay
  were denied; one exact expired record was forgotten and all held/active/review records
  remained;
- all six final live evaluations and cleanup checks passed, and the complete offline suite
  passed 146 tests.

Two failed paths were retained as evidence. The first council run had two fenced-JSON format
failures and safely produced no consensus; the fix normalized only the fence before strict
validation. The first due-diligence run lacked a complete fresh portfolio and refused to
promote. See the
[sixth-pass evidence](../evidence/2026-07-16-sixth-pass-deep-agents.md) for exact run IDs,
provider degradation, source contracts, caveats, and cleanup.

## Seventh-pass deep operations

```bash
PYTHONPATH=src python3 experiments/run_dreaming_review_matrix.py
PYTHONPATH=src python3 experiments/run_memory_transparency_agent.py
PYTHONPATH=src python3 experiments/run_contract_drift_sentinel.py
PYTHONPATH=src python3 experiments/run_project_memory_os.py
PYTHONPATH=src python3 experiments/run_adversarial_dissent_council.py
PYTHONPATH=src python3 experiments/run_migration_reconciler.py
```

Final observed outcomes:

- matched eight-document instant/dynamic corpora produced two inferred candidates on the
  first instant run and zero on the repeat; dynamic Dreaming remained pending for all eight
  documents in both runs, so no review action was taken;
- a signed subject export enumerated four actual documents, including provider backing records
  for direct memory writes, plus two current memories and lineage; drift, wrong approval, and
  replay were denied before one exact document/memory erasure passed;
- a 32-path OpenAPI snapshot plus 26 current issue reports produced a non-authoritative
  `HOLD-FOR-CONTRACT-TESTS`; unchanged evidence survived restart and a changed contract digest
  became stale;
- all six acquisition channels were healthy after sourcing the intended local secret file,
  but the research gate still labeled the evidence insufficient rather than conflating API
  health with source quality;
- the project OS recovered a signed four-state chain, required a sandbox-verified artifact for
  review/completion, ignored a forged checkpoint, and excluded another tenant and poison;
- three valid model votes produced `HOLD`, `PILOT`, `HOLD`; the evidence-bound minority dissent
  persisted through restart while any evidence change invalidated the proposal;
- a ten-record migration replayed to the same IDs after simulated acknowledgement loss,
  reconciled exactly in a fresh process, rolled back only the approved IDs, and retained a
  pre-existing target record;
- all final cleanup checks passed and the complete offline suite passed 173 tests.

Failed attempts remained fail-closed. An export parser initially missed the observed
document-list field name; an assertion omitted direct-memory backing documents; stale inherited
provider credentials produced 401s until the intended ignored environment file was sourced;
and malformed project proposals created no checkpoints. See the
[seventh-pass evidence](../evidence/2026-07-16-seventh-pass-deep-operations.md) for exact run
IDs, source contracts, implementation boundaries, and unresolved gaps.

## Eighth-pass practical agent expansion

```bash
PYTHONPATH=src python3 experiments/run_meeting_commitment_steward.py
PYTHONPATH=src python3 experiments/run_memory_intake_firewall.py
PYTHONPATH=src python3 experiments/run_tool_apprenticeship_agent.py
PYTHONPATH=src python3 experiments/run_memory_quality_auditor.py
PYTHONPATH=src python3 experiments/run_least_privilege_worker.py
PYTHONPATH=src python3 experiments/run_all_provider_readiness_commander.py
```

Final observed outcomes on 2026-07-17:

- a real Markdown upload produced ordered chunks, a temporary HTTPS file URL, two exact
  owner/date commitments, a fresh-process due brief, wrong-approval/replay denial, and complete
  cleanup; the URL itself was never serialized;
- the intake firewall stored one expiring preference and one purpose-filtered conversation,
  while denying or reviewing secret, health, implicit, and purpose-expanded writes;
- the tool apprentice recorded two signed read episodes, passed 4/4 egress-blocked checks,
  promoted one skill, ignored unsigned poison, and disabled it on simulated contract drift;
- the quality auditor found canonical contradiction, injection, missing provenance, and secret
  classes, quarantined exactly two critical records, and left the contradiction for review;
- the delegated worker received one container key: other-container read/write returned `403`,
  revocation returned `401`, and a two-request key returned `[200, 200, 429]` with
  `Retry-After`;
- the combination harness enumerated 255 subsets, mapped 28 pairs, identified four prior
  pairwise gaps, and closed them in an all-provider run whose seven-citation report stayed
  `REVIEW` with no action authority;
- cleanup passed for every final run and the complete package-aware offline suite passed 208
  tests.

Failed attempts also remained safe. An invalid SuperServe network shape returned `400` before
execution; the first all-provider report omitted model-authored markers and wrote nothing. The
final design pins the sandbox network contract and makes campaign, decision, action, and
citation fields application-owned rather than model-formatted. See the
[eighth-pass evidence](../evidence/2026-07-17-eighth-pass-practical-agent-expansion.md).

## Ninth-pass resilience, freshness, and operations

Five final hosted runs passed:

- the citation guardian replaced a source revision, rejected the stale V1 snapshot, accepted
  only exact current V2 quotes, persisted one answer, and denied wrong approval/replay;
- the profile-schema steward received five valid suggestions, rejected a plan after concurrent
  drift, preserved both prior buckets, applied the exact additive schema, and routed the new
  marker without a tenant leak;
- the continuity gateway served explicitly labeled signed stale context to a standard request,
  failed high risk closed without an LLM call, skipped the backend while open, rejected a
  tampered/wrong-class cache, and recovered half-open;
- the bulk controller injected one `429`, reduced 8→4, resumed a 24-record manifest from a
  signed 9-record checkpoint, observed exact inventory with 16 documents still processing,
  then reached 24/24 done and searchable;
- the SLO monitor ran 12 profile/memories/hybrid/documents canaries at 100% success and zero
  leaks, then detected a separately injected forbidden result without exposing it to the
  alerting model.

All ten final containers were deleted. The complete package-aware suite passed 238 tests. The
single-run latency values are regression anchors, not service-level claims: the SLO probe saw
806 ms p50 and 1.31 s p95 client wall time, while the asynchronous profile suggestion took
25.4 seconds. See the
[ninth-pass evidence](../evidence/2026-07-17-ninth-pass-resilience-and-freshness.md).

Run the five agents with:

```bash
PYTHONPATH=src python3 experiments/run_source_revision_citation_guardian.py
PYTHONPATH=src python3 experiments/run_profile_schema_evolution_steward.py
PYTHONPATH=src python3 experiments/run_memory_outage_continuity_gateway.py
PYTHONPATH=src python3 experiments/run_adaptive_bulk_ingestion_controller.py
PYTHONPATH=src python3 experiments/run_memory_slo_canary_monitor.py
```

## Tenth-pass capacity, connectors, evaluation, and recovery

Five boundary experiments produced four positive proofs and one typed external block:

- governed connector onboarding denied wrong authorization before I/O, then classified hosted
  create `403` as `plan-or-entitlement-blocked`; it created no OAuth link, connection,
  resource selection, sync, or document;
- the maximum-cardinality audit locally rejected 601 documents and 101 delete IDs, submitted
  exactly 600, observed 78 still processing in the immediate exact inventory, reached 600/600
  done/searchable, then resumed after two batches and completed six exact 100-ID deletions;
- the concurrent challenger produced 20/20 correct sequential and 20/20 correct eight-worker
  profile/memories/hybrid/documents reads with zero errors or tenant leaks, reducing wall time
  from 13.87 seconds to 2.15 seconds in the bounded sample;
- the blinded domain benchmark scored retrieval 100/100 and memory answers 100/100 versus
  10/100 no-memory controls, with zero errors, leaks, or injection bypasses; search p50/p95 was
  671.4/1,017.8 ms and answer p50/p95 was 1,246.7/2,203.5 ms;
- the v0.0.5 recovery drill matched a 51-file, 378,216,164-byte source to its stopped backup,
  preserved direct-memory search/profile across restart and byte-identical clean restore, and
  verified deletion. Its production gate stayed false because shutdown returned signal `-5`,
  four detached workers needed reaping, an earlier v3 ingest stayed queued for 180 seconds,
  and no newer release existed for an upgrade rehearsal.

The first 600-record attempt timed out after 60 seconds with unknown acknowledgement and later
empty inventory; timeout typing and exact inventory reconciliation were added before the final
run. The first 100-case attempt failed ten recent queries and ten citations; trusted retrieval
queries and nested chunk rendering were fixed without changing the hidden rubric. The first
self-host recovery attempt exposed the queue wedge, shutdown panic, and orphan worker. These
failures are part of the evidence rather than discarded warm-ups. See the
[tenth-pass evidence](../evidence/2026-07-17-tenth-pass-capacity-connectors-and-recovery.md).

Run the hosted experiments with:

```bash
PYTHONPATH=src python3 experiments/run_governed_connector_onboarding.py
PYTHONPATH=src python3 experiments/run_max_cardinality_capacity_audit.py
PYTHONPATH=src python3 experiments/run_concurrent_four_surface_recall_challenge.py
PYTHONPATH=src python3 experiments/run_blinded_domain_100_benchmark.py
```

The local recovery runner deliberately requires explicit disposable paths:

```bash
PYTHONPATH=src python3 experiments/run_self_host_backup_restore.py \
  --server-binary /path/to/supermemory-server \
  --source-data-dir /tmp/supermemory-recovery-source \
  --provider-env /path/to/provider.env
```

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

The tenth pass completed stopped-state backup, same-directory restart, clean-directory restore,
and direct-memory deletion durability. Before production, still add or repeat:

- upgrade from the exact currently deployed version;
- queued-ingestion recovery and clean supervised shutdown with no detached worker;
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

The local ten-surface framework matrix and the patched one-question MemoryBench/OpenRouter run
are now implemented. The former validates scoped recall/capture contracts without installing
third-party runtimes. The latter completed all phases but retrieved zero context and scored
incorrect, then deleted and verified all 19 documents. Runbooks:

```bash
PYTHONPATH=src python3 experiments/run_framework_integration_contract_matrix.py
integrations/memorybench-openrouter/verify.sh /path/to/clean-memorybench-checkout
```

- exercise approve/decline/undo on a generated inference with at least two independent parents;
  a larger instant corpus produced two one-parent candidates once and zero on repeat;
- deliberately expire or revoke one provider credential and repeat the healthy six-channel
  acquisition run to retain both full and typed-degradation regressions;
- measure council calibration, model/order effects, correlated errors, and abstention beyond
  the passing genuine-minority-dissent case;
- replace the tutor's toy grade with a validated domain assessment and measure false mastery;
- exercise retention across connectors, backups, caches, export, and self-hosted restore;
- repeat both Dreaming modes across larger related batches, longer windows, and queue/readiness
  instrumentation; instant candidate generation was non-deterministic and dynamic stayed pending;
- batch file upload and the exact 50 MB/content-type rejection boundaries; the 600-document
  ingest and 100-ID exact-delete boundaries now pass;
- repeat the completed 100-case blinded domain suite on realistic product data and volume;
- file upload formats and the exact 50 MB rejection boundary beyond the passing Markdown path;
- connector sync/update/delete on an entitled plan;
- expanded scoped-key endpoint matrix beyond passing single/multi-scope read/write, revocation,
  and `429`/`Retry-After` controls;
- higher-order provider degradation/order matrices beyond complete pair coverage;
- model-router holdouts, exploration/expiry, and repeated end-to-end economics;
- temporal recall across timezones, recurrence, corrections, and larger corpora;
- dependency guardian fail-closed controls using known-vulnerable and ambiguous packages;
- Router outage fail-open behavior and token headers;
- self-hosted real-version upgrade, queued-ingestion/shutdown recovery, and large-file regressions;
- SMFS mount concurrency and bidirectional 30-second sync;
- diagnose the MemoryBench smoke's zero-result retrieval, then run two public datasets with the
  tested OpenRouter overlay and exact cleanup.
