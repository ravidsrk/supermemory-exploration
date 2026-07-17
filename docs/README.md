# Supermemory practical wiki

This is a dated, evidence-driven operating manual for evaluating and building with
Supermemory over the next six months. It is not a copy of the product documentation.

## Start here

1. [Practical multi-provider agents](practical-agents.md) — live builds and runbooks.
2. [Provider combination map](provider-combinations.md) — useful pairings and anti-patterns.
3. [Practical verdict](verdict.md) — where Supermemory is strong, weak, and fit for use.
4. [Capability map](capability-map.md) — every material surface and its maturity.
5. [Memory model](memory-model.md) — documents, chunks, memories, profiles, graph history,
   containers, and the read/write lifecycle.
6. [Agent architectures](agent-architectures.md) — build patterns and product ideas.
7. [Production playbook](production-playbook.md) — isolation, safety, latency, lifecycle,
   and operational guidance.
8. [Experiments](experiments.md) — what the lab actually observed.
9. [Current source inspection](source-internals.md) — agent SDK and MemoryBench internals.
10. [Ecosystem and source notes](ecosystem.md) — SDKs, plugins, MCP, connectors, SMFS,
   self-hosting, and public repository findings.
11. [Benchmarks](benchmarks.md) — MemoryBench, MemScore, benchmark caveats, and eval plan.
12. [Six-month roadmap](roadmap.md) — a staged adoption and retest schedule.

## Evidence language

Every important conclusion uses one of these labels:

| Label | Meaning |
|---|---|
| **Documented** | Stated in current official documentation. |
| **Source-inspected** | Confirmed in a pinned public repository or generated SDK. |
| **Observed** | Reproduced by this lab against a hosted or local system. |
| **Reported** | Found in an open issue or third-party account; not reproduced here. |
| **Inferred** | A design conclusion derived from the evidence. |

“Observed” is strongest for behavior but is still a sample from one account, region,
date, and small synthetic workload. Product behavior, entitlements, and latency can
change. The first-pass observations are dated **2026-07-16**; the latest pass is dated
**2026-07-17**.

The second pass on the same date adds safe live tool execution, a 15-case governance suite,
a six-provider signal radar, a 120-search retrieval-policy grid, and a test-guided release
rehearsal. See the [curated evidence](../evidence/2026-07-16-second-pass-agents.md).

The third pass adds correction-aware personalization, preview-gated erasure, seven filter
shapes, expiry/cancellation, workspace merge, a Router continuity matrix, and a 12-case
matched memory/no-memory benchmark. See the
[lifecycle and benchmark evidence](../evidence/2026-07-16-third-pass-lifecycle-and-benchmark.md).

The fourth pass adds hierarchical organization/project/user context, a fresh-evidence
promotion council, a self-repairing model router, natural-language temporal recall, and an
exact-version dependency guardian. See the
[memory-native agent-systems evidence](../evidence/2026-07-16-fourth-pass-agent-systems.md).

The fifth pass adds governed graph corrections, signed/restartable multi-agent checkpoints,
batch-backed account briefings with a synchronous readiness fallback, incident-hypothesis
falsification, and cost-aware read-tool portfolios. See the
[operational agent-systems evidence](../evidence/2026-07-16-fifth-pass-operational-agents.md).

The sixth pass adds full three-version lineage reconstruction, inferred-review stewardship,
an evidence-bound three-model decision council, assessment-verified adaptive teaching,
resumable budgeted due diligence, live-state-aware change simulation, and legal-hold-aware
retention. It also exercises a real partial-provider outage rather than hiding it. See the
[deep agent-systems evidence](../evidence/2026-07-16-sixth-pass-deep-agents.md).

The seventh pass adds a larger instant/dynamic Dreaming and inferred-review comparison,
subject-level export and exact erasure, OpenAPI/issue contract-drift holds, a signed
long-horizon project state machine, genuine valid minority dissent, and resumable batch
migration with exact reconciliation and rollback. It also restores a healthy six-provider
research path after detecting stale process credentials. See the
[deep operations evidence](../evidence/2026-07-16-seventh-pass-deep-operations.md).

The eighth pass adds file-upload meeting commitments, consent-bound memory intake, verified
tool apprenticeship, contamination auditing, a truly scoped delegated worker, and systematic
eight-provider combination coverage. It live-tests file/chunk/temporary-URL behavior,
purpose filters, exact quarantine, `403` scope boundaries, immediate `401` revocation,
`429` plus `Retry-After`, all 28 provider pairs, and a governed all-provider review. See the
[practical-agent expansion evidence](../evidence/2026-07-17-eighth-pass-practical-agent-expansion.md).

The ninth pass adds exact source-revision citations, governed profile-schema evolution,
risk-aware stale-memory continuity, resumable backpressure-aware bulk ingestion, and signed
four-surface memory SLO canaries. It live-proves stale-source refusal, concurrent schema-drift
denial, high-risk fail-closed outage behavior, a 24-document acceptance/processing distinction,
and profile/memory/hybrid/document isolation monitoring. See the
[resilience and freshness evidence](../evidence/2026-07-17-ninth-pass-resilience-and-freshness.md).

The tenth pass governs connector onboarding through the entitlement/OAuth boundary, proves
the exact 600-document ingest and six-by-100 deletion lifecycle, challenges all four recall
surfaces with eight concurrent workers, completes a blinded 100-case matched benchmark, and
performs stopped-state self-host backup, restart, and byte-identical clean restore. It also
records the operationally important negative results: connector entitlement `403`, local
queued-ingestion wedge, signal-5 shutdown, detached workers, and no newer upgrade target. See
the [capacity, connectors, evaluation, and recovery evidence](../evidence/2026-07-17-tenth-pass-capacity-connectors-and-recovery.md).

## Update discipline

- Retest the core probe monthly and before a production launch.
- Pin SDK versions; review the changelog and open issues before upgrading.
- Never replace a dated observation silently. Add the new result and state what changed.
- Keep raw runs in ignored `.runs/`; commit only reviewed, secret-free summaries.
- Treat vendor benchmark claims as hypotheses until reproduced on the product's own data.

The official machine-readable docs index is
[docs/llms.txt](https://supermemory.ai/docs/llms.txt). The public monorepo and
MemoryBench are on [GitHub](https://github.com/supermemoryai/supermemory) and
[GitHub](https://github.com/supermemoryai/memorybench), respectively.
The upstream monorepo and this independent field lab are MIT-licensed; source-inspected,
hosted-observed, and lab-original claims remain explicitly distinguished.
