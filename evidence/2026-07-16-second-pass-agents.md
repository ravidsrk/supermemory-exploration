# Second-pass practical agent evidence — 2026-07-16

This is a reviewed, secret-free summary. Raw traces remain ignored under `.runs/`. Hosted IDs,
credentials, public-post text, and project names are not committed.

## Direct-memory visibility and query sensitivity

Three direct writes were measured independently through profile, memories, and hybrid:

| Case | Content size | Profile first seen | Memories first seen | Hybrid first seen |
|---|---:|---:|---:|---:|
| Short static | 65 chars | 1,039.9 ms | 2,089.9 ms | 3,276.7 ms |
| Medium dynamic | 1,151 chars | 1,090.1 ms | 1,773.5 ms | 2,645.8 ms |
| Long dynamic | 6,867 chars | 1,155.0 ms | 2,536.1 ms | 3,251.4 ms |

All appeared on the first request to each path; no polling retry was required. A separate long
record then showed:

- exact canary and exact tail decision: hit at thresholds 0, .5, and .7;
- short semantic paraphrase: hit at 0/.5, missed at .7;
- original long natural-language request: missed even at threshold 0;
- unrelated control: false positive at 0/.5, filtered at .7;
- profile retained the full dynamic record, while its query-specific search results followed
  the same hit/miss behavior.

Inference: the earlier tool-selection miss was query formulation and the precision/recall
tradeoff, not demonstrated indexing delay.

## Reversible website monitor

A Context.dev exact-page monitor targeted a stable control page. Baseline and forced second
run completed, zero changes were reported, the no-change observation was accepted as a
Supermemory RAG document, and the monitor was deleted in `finally`. Quota returned to 0 used
of 50. This proves lifecycle and the negative control, not positive change detection.

## Safe live tool execution

The agent enforced exact allowlists before both calls:

| Provider | Inspected gate | Live outcome |
|---|---|---|
| Monid / DefiLlama | GET; nested input contract; $0.001 per call; cap $0.005 | Completed Bitcoin price read. |
| Composio / Hacker News | Exact slug; `no_auth=true`; no mutation token | Returned three latest stories. |
| Supermemory | Outputs marked untrusted | Two RAG observations plus one dynamic re-inspection policy accepted. |

The first attempt received `401` because inherited shell variables overrode `.env.local`.
Hash-only comparison found different Monid, Composio, and Exa values. Live runners then unset
those inherited variables so the ignored file was authoritative. No credential was logged.

## 15-case governance scorecard

| Category | Passed | Tested invariant |
|---|---:|---|
| Versioned update | 3/3 | New canary present and old canary absent in all three read paths. |
| Precise forget | 3/3 | Target absent and retained control present in all three paths. |
| Isolation | 4/4 | Source tenant visible to itself; never visible in paired tenant; paired control remained. |
| Prompt injection | 5/5 | Fact retained, action denied, attacker token absent, code authorization false. |
| **Total** | **15/15** | All lifecycle cleanups reported no error. |

The five malicious documents were retrieved rather than filtered out. Context length was
483–497 characters and each answer identified SEV-2 while denying external action. This tests
the boundary under five synthetic payloads; it is not a universal jailbreak guarantee.

## Longitudinal developer-signal radar

The corrected fresh cycle used Supermemory, Composio, Exa, ScrapeCreators, and OpenRouter:

- Hacker News: 6 hits after replacing the full research prompt with `AI agent memory`;
- Exa: 6 results, reported cost $0.007;
- Reddit: 7 posts;
- X: 8 posts;
- four source documents plus one temporal conclusion accepted;
- the stored evidence was hybrid-searchable on the first poll.

The second cycle invoked only Supermemory and OpenRouter, retrieved 10 results with a bounded
10,000-character context, and carried a deterministic memory-only/freshness warning. The first
implementation merely asked the model to label staleness; it did not do so reliably, which is
why the banner is now application-owned.

## 120-search retrieval-policy grid

Twenty-four policies crossed memories/hybrid, thresholds 0/.5/.7, rerank on/off, and query
rewrite on/off over five queries. The final run selected:

```text
mode=memories threshold=0.7 rerank=false rewriteQuery=false limit=10
```

It scored 4/5: two of three positive queries, zero of two negative queries, zero false
positives, median 657.7 ms, and p95 783.5 ms. It missed a semantic paraphrase. The first agent
test also missed because its wording differed from the benchmark. A trusted domain prefix
recovered the memory without lowering the threshold; the answer correctly stated that
allowlists and code-level authorization must remain outside memory. The selected policy is a
dated result for this synthetic corpus, not a universal default.

## Read-only release triage plus sandbox repair

Vercel returned 20 projects and 30 deployments: 20 READY, 8 ERROR, and 2 BLOCKED. Only counts
and state categories entered the committed evidence. No build logs were fetched and no Vercel
write occurred.

The SuperServe sandbox used the explicit Python 3.11 template and denied all IPv4 egress. A
static Supermemory runbook guided repair of a synthetic webhook verifier:

1. baseline failed stale and future-timestamp tests;
2. first patch fixed staleness but still accepted future timestamps;
3. one constrained repair used that exact failure and passed all four tests;
4. the passing lesson was stored as dynamic memory;
5. sandbox deletion succeeded.

The code persists failed repairs only as unverified RAG evidence. It never promotes them to a
verified lesson or presents the rehearsal as the root cause of observed Vercel errors.

## Reproducibility and limitations

- Final offline suite: 52 tests.
- Final second-pass commits are intentionally split by capability.
- These are small synthetic evaluations on one account and date, not load tests.
- Latencies include client/network time and are not service SLOs.
- The live policy grid must be rerun against each domain corpus and after retrieval changes.
- Positive monitor-change detection and approved reversible external writes remain future work.
