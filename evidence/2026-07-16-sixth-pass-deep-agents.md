# Sixth-pass evidence: deep agent systems

Date: **2026-07-16**

Environment: hosted Supermemory and live provider APIs, synthetic `lab:` containers,
read-only operational observations, three independent OpenRouter models, and disposable
egress-blocked sandboxes

Scope: graph lineage and inferred review, multi-model deliberation, adaptive teaching,
resumable multi-provider due diligence, operational change-risk simulation, legal-hold-aware
retention, negative controls, credential degradation, cleanup, and current source inspection

This is a reviewed, secret-free digest. Raw traces remain ignored in `.runs/`. Results are
point-in-time observations from one account and small synthetic workloads; they are not
availability, latency, pricing, legal, compliance, or model-quality guarantees.

## What was built

| Agent | Providers | Production question | Final run |
|---|---|---|---|
| Graph lineage and review steward | Supermemory + OpenRouter | Can an agent reconstruct a three-version correction chain and keep inferred-memory review behind exact human authorization? | `graph-review-20260716152536-eb6ff4` |
| Multi-model decision council | Supermemory + three OpenRouter models | Can independent models vote from exact evidence, preserve abstention/dissent, and produce only a stale-aware proposal? | `decision-council-20260716153206-673c51` |
| Adaptive tutor | Supermemory + OpenRouter + SuperServe | Can mastery survive restarts while only a verified isolated assessment may change it? | `adaptive-tutor-20260716153536-384f76` |
| Budgeted due-diligence campaign | Supermemory + Context.dev + Exa + ScrapeCreators + Monid + Composio + OpenRouter | Can long research resume from a signed checkpoint, account for calls/costs, cite exact sources, and degrade honestly when providers fail? | `due-diligence-20260716154238-736c80` |
| Operational change-risk board | Supermemory + Vercel + Context.dev + SuperServe + OpenRouter | Can live health override a passing rehearsal while deploy authority remains outside the model and memory? | `change-risk-20260716154622-ec21fa` |
| Legal-hold-aware retention controller | Supermemory + OpenRouter | Can expiry candidates, legal holds, drift, approval, replay, erasure verification, and external audit coexist safely? | `retention-20260716154909-2a631c` |

All six final evaluations passed. Cleanup deleted every created synthetic container and
sandbox, or confirmed an intentionally empty control was already absent. The complete offline
suite passed **146 tests**.

## 1. Graph lineage and inferred-memory review steward

Implementation: [`graph_review_steward.py`](../src/supermemory_lab/graph_review_steward.py),
[`run_graph_review_steward.py`](../experiments/run_graph_review_steward.py), and
[`test_graph_review_steward.py`](../tests/test_graph_review_steward.py).

The steward created one exact fact, revised it twice with versioned updates, loaded current
inventory, and audited version, parent, and root continuity. It separately seeded related
source patterns with `dreaming=instant`, polled the inferred-memory queue for 90 seconds, and
kept review authority in an exact application-owned authorization ledger.

Observed:

- The latest list entry was version 3 and its nested `history` contained versions 1, 2, and 3.
- Every parent link and the common root were valid; the lineage audit passed.
- `historyFieldPresent` was true. This corrects the fifth-pass interpretation: superseded v1
  was not a separate top-level current entry, but it was available inside the current entry's
  history array.
- No inferred-review candidate appeared in the bounded 90-second run.
- Attempting to review an ordinary, non-inferred memory returned 409, so the negative control
  failed closed.
- Approval binds action, candidate ID, content hash, and reviewer; decline and undo follow
  different deterministic support/ledger rules. The model can explain but never review.
- Cleanup removed two documents and two memories.

The current OpenAPI describes `/v4/memories/list` as returning latest entries with update
history and exposes `history`, parent/root fields, and `memoryRelations` in its schema
([current OpenAPI](https://api.supermemory.ai/v3/openapi)). The official memory-review guide
documents the inferred queue plus approve, decline, and undo transitions
([memory review](https://supermemory.ai/docs/memory-review)). Graph relations distinguish
updates, extensions, and derivations ([graph memory](https://supermemory.ai/docs/concepts/graph-memory)).

This proves version reconstruction for one three-version synthetic chain, not a complete
audit-export guarantee. The inferred endpoint contract and fail-closed negative case are
covered, but approve/decline/undo still need a genuinely generated candidate.

## 2. Evidence-bound multi-model decision council

Implementation: [`decision_council.py`](../src/supermemory_lab/decision_council.py),
[`run_decision_council.py`](../experiments/run_decision_council.py), and
[`test_decision_council.py`](../tests/test_decision_council.py).

Three model families deliberated independently over the same immutable evidence manifest:
`openai/gpt-4.1-nano`, `google/gemini-2.5-flash-lite`, and
`mistralai/mistral-small-3.2-24b-instruct`. Each vote had a strict schema, cited only manifest
evidence IDs, named a recommendation and confidence, and supplied a falsifier. Quorum was
computed in trusted code. Votes and the signed proposal were persisted separately from raw
evidence; neither granted action authority.

Observed:

- Retrieved poison was present in context and absent from all valid votes.
- All three final votes were schema-valid and evidence-bound; the recommendation was
  unanimously `STAGED` and remained a `proposal`.
- No live dissent occurred. Unit tests preserve invalid-schema, unknown-citation, injected
  marker, and valid-minority-dissent paths so disagreement is not averaged away.
- A fresh process loaded `current-proposal`; changing the evidence digest changed the status
  to `stale-evidence`.
- The proposal crossed its exact visibility barrier; `action_authorized` remained false.
- Cleanup removed eight documents and two memories.

The first run, `decision-council-20260716153057-3dbee7`, had only one valid vote because two
providers wrapped otherwise JSON output in Markdown fences. The council returned no consensus
and no action. The final parser added one narrow code-fence normalization step while retaining
strict schema, citation, poison, quorum, and falsifier checks. This is a format-compatibility
repair, not a relaxation of evidence validation.

## 3. Assessment-verified adaptive tutor

Implementation: [`adaptive_tutor.py`](../src/supermemory_lab/adaptive_tutor.py),
[`run_adaptive_tutor.py`](../experiments/run_adaptive_tutor.py), and
[`test_adaptive_tutor.py`](../tests/test_adaptive_tutor.py).

Mastery is a signed application record containing subject, skill, score, evidence, assessment
time, next review, and version. The signature key stays outside memory. Trusted code verifies
the record, applies temporal decay, and selects a deterministic lesson mode; the model may
teach but cannot grade or update mastery. An egress-blocked sandbox verifies an assessment
before the application creates the next version.

Observed:

- A signed baseline score of 0.30 was due for review and selected `worked-example`.
- An unsigned retrieved poison record claiming score 1.0 and “skip assessment” was ignored;
  its instruction was absent from the lesson.
- The sandbox grade passed 4/4 and the sandbox was deleted. Reusing the same grade without its
  verification record was denied.
- Verified evidence created mastery version 2 at 0.72.
- A fresh process recovered score 0.72 and selected `guided-practice`; the empty control had
  no mastery.
- Cleanup removed two documents and two memories; the empty control was already absent.

This pattern applies to coaching, onboarding, compliance training, coding practice, and
rehabilitation support only when the domain's real assessment is valid. A sandbox can verify a
deterministic coding exercise; it cannot substitute for clinical, legal, or educational
judgment.

## 4. Resumable, budgeted due-diligence campaign

Implementation: [`due_diligence_campaign.py`](../src/supermemory_lab/due_diligence_campaign.py),
[`run_due_diligence_campaign.py`](../experiments/run_due_diligence_campaign.py), and
[`test_due_diligence_campaign.py`](../tests/test_due_diligence_campaign.py).

The campaign treats long research as a recoverable job. A signed checkpoint binds campaign,
query, evidence manifest, call ledger, known cost, unknown-cost providers, failures, and next
stage. Acquisition has both a call cap and monetary reservation. Every evidence record tracks
the provider and original publisher so multiple APIs repeating one page cannot manufacture
corroboration. Only exact evidence IDs may be cited.

Observed:

- Context.dev, public X, and Reddit produced three relevant records from three publishers,
  including official evidence; each was stored as source evidence.
- Exa, Monid, and Composio returned 401 authentication failures in this point-in-time run.
  Those same credentials had authenticated in earlier passes, so this is credential/external
  state regression, not evidence that the provider integrations are inherently unavailable.
- The campaign made six bounded acquisition calls, reserved $0.01 in known point-in-time cost,
  and represented non-comparable costs explicitly instead of treating them as zero.
- A fresh process verified and resumed the signed checkpoint.
- The report cited three exact evidence IDs, excluded retrieved poison, and labeled itself
  `degraded-partial`.
- Degraded evidence did not create a promoted conclusion and did not authorize a purchase. A
  memory-only resume was explicitly stale and also could not promote.
- Cleanup removed seven documents and two memories.

The earlier run `due-diligence-20260716154007-a178d8` initially had only three usable sources
and correctly failed the stricter fresh-portfolio gate. The final design distinguishes
`ready`, `degraded-partial`, and `memory-only-stale`; only a complete fresh portfolio is
promotion-eligible. This is preferable to hiding partial provider failure behind fluent prose.

## 5. Operational change-risk simulation board

Implementation: [`change_risk_board.py`](../src/supermemory_lab/change_risk_board.py),
[`run_change_risk_board.py`](../experiments/run_change_risk_board.py), and
[`test_change_risk_board.py`](../tests/test_change_risk_board.py).

The board combines minimized, read-only live state with official rollout guidance and a
synthetic isolated rehearsal. Evidence classes remain separate. A deterministic health gate
owns the recommendation, so a passing rehearsal cannot override unhealthy current state. The
signed advice binds the live snapshot and becomes stale if the snapshot changes.

Observed:

- Read-only Vercel inspection counted 20 projects and 30 deployments without persisting names.
- Deployment states were 20 `READY`, 8 `ERROR`, and 2 `BLOCKED`.
- The egress-blocked staged-rollout simulation passed 5/5 and its sandbox was deleted.
- Live health still forced `HOLD`, which was the expected recommendation.
- Retrieved poison was absent from the explanation; deploy authorization remained false.
- The advice was visible and a fresh process loaded `current-advice`; a changed snapshot
  produced `stale-evidence`.
- Cleanup removed five documents and two memories.

The official Vercel guidance recommends gradual rollouts with observability and rollback
controls ([rolling releases](https://vercel.com/docs/rolling-releases)). The live account
counts here are only a synthetic risk signal: without the service's deployment intent, logs,
SLOs, or ownership data, `HOLD` is a safe rehearsal decision, not a production diagnosis.

## 6. Legal-hold-aware retention controller

Implementation: [`retention_controller.py`](../src/supermemory_lab/retention_controller.py),
[`run_retention_controller.py`](../experiments/run_retention_controller.py), and
[`test_retention_controller.py`](../tests/test_retention_controller.py).

The controller loads unfiltered latest inventory, then partitions exact IDs in trusted code by
subject, retention class, `retainUntil`, legal hold, and ambiguous-review state. The model may
explain a plan but never select IDs. A legal-hold authorization is bound to the exact inventory
snapshot; placing the hold creates a versioned memory and invalidates the prior retention plan.
The revised deletion approval binds plan ID, digest, exact IDs, actor, and one-time use. Audit
events go to an external canonical sink.

Observed:

- The initial partition was forget 2, protected 1, retained 1, and review 1.
- A mismatched hold authorization was denied. The exact authorization created version 2 with
  the expected parent and changed the partition to forget 1 and protected 2.
- Applying the old plan after the hold was denied as drift.
- Wrong-plan approval was denied; the exact revised approval forgot one ID; replay was denied.
- The forgotten record was absent. Both held records, the active record, and the ambiguous
  review record remained.
- The external sink recorded `legal-hold-placed` and `retention-forget` events.
- Retrieved poison was absent from the explanation; cleanup removed two documents and six
  remaining memories.

Supermemory documents precise forgetting and natural-language matching
([memory operations](https://supermemory.ai/docs/memory-operations)). This lab uses exact IDs
for execution because semantic matching is useful for discovery but is not proof that a legal
retention policy selected every and only eligible record. Whether any design satisfies a real
legal hold depends on jurisdiction, contracts, backups, connectors, logs, and counsel—not only
the primary memory API.

## Cross-agent conclusions

1. **Memory is most valuable as evidence, learning, and recovery—not authority.** Review,
   grading, purchase, deployment, legal hold, retention execution, and replay state remained
   deterministic or external.
2. **Bind durable advice to the evidence snapshot.** Council proposals, campaign checkpoints,
   rollout advice, and deletion plans all become stale when their evidence digest changes.
3. **Negative controls define the production contract.** Ordinary-memory review, poison,
   forged/unsigned mastery, invalid model JSON, unknown citations, provider 401s, empty memory,
   unhealthy live state, wrong approvals, drift, and replay were exercised.
4. **A degraded partial result is a successful state when it is honest.** It must retain
   sources, failures, and remaining questions while refusing promotion or action.
5. **Current inventory and historical reconstruction are one response with two levels.** The
   top-level list is latest truth; the nested history reconstructs prior versions for the
   observed chain.
6. **Models can explain and propose, but trusted state must decide.** This boundary survived
   three model families, retrieved injection content, restarts, and changing evidence.
7. **Retention needs a system outside the memory being governed.** Exact authorization,
   replay denial, immutable audit, connector/back-up handling, and policy interpretation cannot
   safely live only in the data being deleted.

## Current primary sources and source inspection

- [Supermemory current OpenAPI](https://api.supermemory.ai/v3/openapi) — machine-readable
  hosted API contract, including memory list/history and current v3/v4 surfaces.
- [Supermemory memory review](https://supermemory.ai/docs/memory-review) — inferred queue and
  approve/decline/undo workflow.
- [Supermemory graph memory](https://supermemory.ai/docs/concepts/graph-memory) — update,
  extension, and derivation relationships.
- [Supermemory changelog](https://supermemory.ai/changelog/) and
  [API changelog](https://supermemory.ai/changelog/api/) — dated product/API changes including
  memory review, Dreaming recovery, forget matching, and natural time.
- [Supermemory MIT-licensed monorepo](https://github.com/supermemoryai/supermemory), inspected
  at commit `8d926332ab23aa5785def636aca9d0a52fea4a65` — review hooks/UI, schemas, generated clients,
  and relation rendering.
- [Official Supermemory X account](https://x.com/supermemory) — current public product signals;
  social posts were treated as dated evidence, not API contracts.
- [Official local-development announcement](https://x.com/supermemory/status/2064749494412222583)
  — a public signal for `npx supermemory local`, corroborated against repository/docs before
  implementation decisions.

Current open issues are reports, not reproduced facts. The official repository currently has
reports concerning profile bucket migration, middleware fail-closed behavior, Python SDK
deduplication, MCP graph scope, add-memory defaults, and query-mode duplication. Review the
[open issue list](https://github.com/supermemoryai/supermemory/issues) and the exact issue
before upgrading an affected integration.

## Contradictions, gaps, and next gates

- The fifth pass said ordinary inventory did not expose v1 and inferred that no current
  history path existed. The sixth pass and current OpenAPI resolve the contradiction: v1 is
  nested under the latest entry's `history`, not returned as a separate current entry. Repeat
  with branches, forget/undo, pagination, and export before treating it as a compliance log.
- The inferred-review contract is documented and ordinary-memory review correctly returned
  409, but no candidate appeared after the bounded instant-Dreaming seed. Generate a real
  candidate, then live-test approve, decline, undo, queue capacity, reviewer races, and audit.
- Three provider credentials that worked earlier returned 401. Refresh Exa, Monid, and
  Composio credentials and rerun both the complete due-diligence path and the degraded path;
  keep circuit breakers and partial-state semantics regardless.
- The council happened to be unanimous. Run adversarial evidence that creates genuine valid
  minority dissent, compare model-order effects, blind the vote order, and measure calibration
  rather than treating plurality as truth.
- Replace the tutor's synthetic recursion task with a domain-specific validated assessment;
  measure forgetting curves, false mastery, accessibility, and human correction.
- Run the change board with an authorized synthetic Vercel project and reversible canary while
  retaining explicit human approval. Never use the shared account inventory as deploy intent.
- Add connector, cache, backup, and self-hosted deletion verification to retention; obtain legal
  review before representing it as a compliance control.
- Run the planned blinded 100-question domain benchmark and sustained latency/cost tracking.
