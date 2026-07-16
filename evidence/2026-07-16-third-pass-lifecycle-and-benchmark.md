# Third-pass lifecycle, Router, and domain-benchmark evidence

Date: 2026-07-16

Scope: hosted Supermemory, Memory Router, and OpenRouter against synthetic isolated containers

Raw traces: ignored under `.runs/`; run IDs are listed for local audit

Safety: no credential values, real tenant data, or private provider resources are included

## What this pass tested

This pass moved beyond create/search demos into five production-shaped workflows:

1. correction-aware personalization with conversation archival, normalized direct facts,
   versioning, custom profile buckets, idempotency, isolation, and whole-container cleanup;
2. preview-gated semantic erasure plus a v4 filter operator matrix;
3. server-enforced memory expiry and expiry cancellation;
4. asynchronous workspace/container consolidation;
5. Memory Router continuity modes and a paired memory/no-memory domain QA benchmark.

The harnesses use the current official [OpenAPI](https://api.supermemory.ai/v3/openapi),
[container settings](https://supermemory.ai/docs/concepts/container-tags),
[profiles](https://supermemory.ai/docs/user-profiles),
[filtering](https://supermemory.ai/docs/concepts/filtering),
[memory review](https://supermemory.ai/docs/memory-review), and
[Router](https://supermemory.ai/docs/memory-router/overview) contracts. Results below are
hosted observations on one account and date, not universal service guarantees.

## Result summary

| Workflow | Final run | Result |
|---|---|---|
| Evolving preference agent | `preference-20260716132955-bdb0e1` | Passed correction, custom bucket, idempotency, isolation, and cleanup |
| Governed erasure agent | `erasure-20260716133626-a98e27` | Passed 7/7 search filters and safe preview/apply deletion core; exposed audit-recovery discrepancy |
| Expiry + consolidation agents | `lifecycle-20260716133948-06c84b` | Expiry, cancellation, merge, source deletion, settings retention, and cleanup passed |
| Router continuity matrix | `router-20260716134439-dd53d3` | Delta/full-history and direct-API pool controls passed; Router-generated cross-session recall failed |
| Domain QA benchmark | `domain-20260716135220-628c9b` | 12/12 retrieval and memory answers versus 2/12 no-memory baseline; all safety gates passed |

## 1. Correction-aware personalization

The agent configures a container-specific entity context and three custom profile buckets,
archives the full role-preserving conversation, explicitly normalizes confirmed preferences,
and versions corrections rather than appending contradictory facts.

Observed:

- the entity context and all three custom buckets persisted;
- the v4 conversation became a completed source document, but automatic preference extraction
  did not appear within the bounded 30-second observation window;
- explicitly writing the confirmed preference and then updating it produced version 2;
- the profile/search answer contained the corrected preference and omitted the old one;
- the corrected fact became visible in about 2.66 seconds in the final run;
- replaying the complete conversation left memory and document counts unchanged;
- a different container could not retrieve the fact;
- the inferred-memory review queue was empty for this synthetic interaction;
- deleting the container removed the experiment.

Practical conclusion: use conversations as the auditable source envelope, but promote
application-confirmed facts explicitly when the next turn depends on them. Do not assume a
queued or even completed conversation has already yielded the desired profile fact.

Two failed rehearsals are retained locally: the first used a generic “any result exists”
barrier and mistook an older seed for the new fact; the second used an ambiguous prompt and
the answer model echoed an experiment marker. The final harness requires an exact canary and
scores semantic answer content separately from retrieval evidence.

## 2. Governed semantic erasure and filters

Seven v4 memory-search filter cases passed:

- scalar equality;
- numeric comparison;
- `array_contains`;
- `string_contains`;
- negation;
- nested AND/OR;
- a dotted metadata key.

The dotted key matters because official filter examples and prose are internally inconsistent
about whether dot notation is allowed. The live search accepted it. Keep a contract test if
your schema relies on dotted fields.

The erasure flow is intentionally two-phase. A semantic dry run must return the exact bounded
candidate set and no protected canary; only that preview authorizes apply. The final run
authorized one target, returned a batch identifier, hid the target from default search, and
left the control memory intact.

Two hosted discrepancies remain:

- `/v4/memories/list` returned no rows when the documented metadata filter was supplied even
  though unfiltered listing returned the memories;
- a directly forgotten memory did not reappear through `include.forgottenMemories=true` or
  memory listing during repeated polling, so the documented audit-recovery path was not
  observed for explicit forget.

The agent therefore treats preview/apply plus a retained-control negative test as the deletion
gate. It does not claim a recoverable audit trail unless the exact deployed account/version
proves one.

## 3. Expiry and workspace consolidation

The incident-lease agent created a short-lived memory using `forgetAfter`. It became hidden
after five polls and about 15.4 seconds. A second memory had its expiry cleared through a
versioned update, reached version 2, and remained visible. Unlike the explicitly forgotten
memory above, the time-expired fact was retrievable when forgotten memories were explicitly
included.

The workspace-consolidation agent queued an asynchronous container merge. Data was already
visible in the target while the merge reported `cleanup_pending`; a bounded waiter later saw
`completed`. The source memory moved, the existing target memory remained, the source
container disappeared, and the target's settings were preserved.

Practical conclusions:

- expiry is useful for incident leases, temporary campaign context, and short-lived agent
  scratch knowledge, but applications should still verify disappearance;
- clearing expiry is a versioned mutation, not an in-place timer edit;
- merge is a state machine, not a synchronous rename;
- route reads to the target during consolidation and retain an application-side merge ledger;
- preserve and verify target settings explicitly because target configuration wins.

## 4. Memory Router continuity matrix

The matrix separated four claims that are often conflated:

- **model continuity:** delta-only continuation replicated 3/3 after 20 seconds, and explicit
  full history answered correctly;
- **direct API memory injection:** a direct memory in the same user pool influenced Router
  answers both with and without a conversation header;
- **tenant isolation:** another user returned `UNKNOWN` and did not receive the canary;
- **Router-generated cross-session memory:** a new conversation did not recall the generated
  session token; it instead saw the unrelated direct API pool memory.

A Router conversation write was visible through the direct API as a hybrid chunk, but it was
not promoted to the distilled memory pool in this observation. The final cleanup removed 12
documents and one direct memory for the primary user plus one control document for the other
user.

Observed prompt-token counts were roughly 194–198 for initial turns, 213–217 for delta-only
continuations, 237 for explicit full history, 296 for the new conversation, and 304 with the
direct API memory pool. This is a small diagnostic sample, not a cost model.

Practical conclusion: Router can be useful as a convenience/compression layer, but it is not
the lab's source of truth. Keep an explicit API path and separately test same-conversation,
new-conversation, direct-pool, isolation, fail-open, and outage behavior.

## 5. Twelve-case domain smoke benchmark

The benchmark used six categories with two cases each: stable facts, updates, temporal
reasoning, multi-hop reasoning, tenant isolation, and prompt-injection evidence. Every case
ran twice against the same question and answer model: once with bounded Supermemory context
and once with no memory/external context.

Final result:

| Metric | Value |
|---|---:|
| Retrieval evidence | 12/12 |
| Memory-assisted answers | 12/12 (100%) |
| No-memory answers | 2/12 (16.7%) |
| Accuracy lift | +83.3 percentage points |
| Search latency p50 | 659.3 ms |
| Search latency p95 | 1,143.3 ms |
| Mean estimated retrieved context | 326.8 tokens |
| Maximum rendered context | 1,310 characters |
| Tenant leaks | 0 |
| Prompt-injection bypasses | 0 |

The two baseline passes were the correct `UNKNOWN` responses for isolation questions; memory
was intentionally unnecessary there. One baseline multi-hop answer hallucinated a region,
illustrating why paired no-context controls are valuable.

The benchmark is deliberately small, synthetic, and unblinded. It is a regression smoke gate,
not an official MemoryBench result and not evidence of production-scale accuracy. The first
two rehearsals also caught evaluation defects: evidence identifiers were incorrectly mixed
into semantic answer scoring, and a strict ISO date scorer rejected the correct written date.
The final harness scores retrieved canaries separately and canonicalizes common date formats.

## Contradictions to keep as regression tests

| Question | Documentation/contract signal | Hosted observation | Operating rule |
|---|---|---|---|
| Default v4 search mode | Overview language can imply hybrid; SDK/OpenAPI say memories | Omission behaved as memories | Always send `searchMode` |
| Dotted filter keys | Official examples/prose conflict | Dotted key worked in search | Contract-test your deployed schema |
| Filtered memory listing | Request shape is in current OpenAPI | Filtered list returned zero while unfiltered list did not | Use search for governed preview; test list independently |
| Forgotten-memory recovery | Include flag suggests audit retrieval | Explicit forget stayed absent; expiry was recoverable | Treat expiry and explicit forget as distinct lifecycles |
| Merge completion | Queue response documents asynchronous work | Data visible at `cleanup_pending`, then `completed` | Wait on merge ID; do not infer completion from data visibility |
| Router persistence | Router promises automatic memory/context | direct pool worked; generated cross-session fact did not | Prototype behind explicit positive controls |

## Reproduction

```bash
PYTHONPATH=src python3 experiments/run_evolving_preference_agent.py
PYTHONPATH=src python3 experiments/run_filter_erasure_agent.py
PYTHONPATH=src python3 experiments/run_lifecycle_agents.py
PYTHONPATH=src python3 experiments/run_router_continuity_matrix.py
PYTHONPATH=src python3 experiments/run_domain_memory_benchmark.py
PYTHONPATH=src python3 -m unittest -v
```

All live scripts create unique `lab:` scopes and attempt cleanup in `finally`. Raw traces are
ignored because even synthetic operational identifiers should be reviewed before sharing.
