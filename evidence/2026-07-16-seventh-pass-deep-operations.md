# Seventh-pass deep operations evidence

Date: **2026-07-16**

Hosted service: Supermemory API

Source snapshot: [`supermemoryai/supermemory@8d92633`](https://github.com/supermemoryai/supermemory/tree/8d926332ab23aa5785def636aca9d0a52fea4a65)

OpenAPI snapshot: [current hosted specification](https://api.supermemory.ai/v3/openapi)

This pass asks whether memory can support user transparency, contract-aware upgrades,
long-horizon project state, genuine model dissent, and resumable migration without becoming
the authority for deletion, deployment, workflow completion, or rollback. It also repeats
Dreaming and inferred-review generation at a larger synthetic size. Raw run artifacts remain
ignored under `.runs/`; this note contains only reviewed, secret-free observations.

## What was built

| System | Memory role | Deterministic control plane |
|---|---|---|
| Dreaming/review matrix | Compare instant and dynamic extraction and inspect the inferred queue | Bounded polling, poison check, and exact review-action binding |
| Memory transparency agent | Enumerate documents, memories, lineage, and source chunks for a subject | Signed export, snapshot-bound exact erasure, replay denial, external audit |
| Contract-drift sentinel | Retain dated API snapshots, current issue signals, and prior advice | Operation/request-schema diff, critical-issue hold, snapshot staleness |
| Project Memory OS | Recall organization, project, and user context across restarts | Signed transition chain, artifact verification, exact external authorization |
| Valid-dissent council | Persist evidence-bound independent recommendations and minority views | Strict vote/citation/falsifier validation, immutable evidence digest, no action authority |
| Migration reconciler | Store a signed manifest, progress checkpoint, and operator explanation | Stable IDs/hashes, exact inventory reconciliation, approval-bound bulk rollback |

## Hosted run results

### Dreaming and inferred review

Runs:

- `dreaming-review-20260716160540-c20661`
- `dreaming-review-20260716160915-d2f932`

Both runs ingested the same shape of eight related documents per mode. All instant documents
and Dreaming jobs completed. All dynamic documents reached `done`, while all eight dynamic
Dreaming jobs remained `dreaming` through the bounded observation window. The first instant
run produced two inferred-review candidates; the repeat produced zero. Dynamic produced zero
in both runs. The first queue candidates each had one parent, below this lab's production
default of two independent parents. No approve/decline/undo transition was therefore applied.
The deliberately poisoned item was not selected and both containers cleaned up.

This is the first hosted candidate-generation observation in the lab, but it is also direct
evidence that identical corpus shapes do not guarantee a stable queue. The current
[memory-review contract](https://supermemory.ai/docs/memory-review) is useful for human
oversight; it is not a synchronous workflow primitive. A complete generated-candidate
approve/decline/undo lifecycle remains open.

### Memory transparency and exact erasure

Final run: `memory-transparency-20260716162157-078ceb`

The first signed export enumerated four documents and two current memories, included the two
explicit source documents and memory history, and excluded another tenant. Four documents is
the important result: direct v4 memory writes also appeared as administrative/backing
documents, so a truthful export must enumerate the provider inventory rather than reconstruct
it only from application write logs.

The agent denied a changed inventory snapshot, wrong authorization, and approval replay. It
then erased one exact source document and one exact memory, verified both absent, retained the
current fact and safe source, and wrote canonical audit events outside Supermemory. Retrieved
prompt poison did not enter the model explanation and the model authorized no operation.
Cleanup removed four subject documents/three memories and one other-tenant document/memory.

### Contract-drift sentinel

Final run: `contract-drift-20260716162728-7f1d40`

The sentinel captured 32 hosted OpenAPI paths and 26 open issue reports from the inspected
GitHub page set. The current schema matched its freshly created baseline, but current reported
wrapper regressions triggered `HOLD-FOR-CONTRACT-TESTS`. That is a release-test recommendation,
not proof that the core API is broken. A fresh process accepted the signed advice against the
same digest; a changed snapshot produced `stale-contract-evidence`.

The acquisition campaign reached Context.dev, Exa, Monid, Composio, X, and Reddit with no
provider failure after the local environment file was sourced. The research promotion layer
still returned `insufficient-evidence` because source relevance/citation requirements were not
met; provider health is not evidence quality. The model had explanation authority only,
retrieved poison was absent, and action authority remained false. Cleanup removed ten
documents and two memories.

The hold was informed by current **reported**, not reproduced, risks such as an unavailable
memory service crashing middleware ([issue #1287](https://github.com/supermemoryai/supermemory/issues/1287))
and Python SDK dedup parsing failures ([issue #1266](https://github.com/supermemoryai/supermemory/issues/1266)).

### Long-horizon project Memory OS

Final run: `project-os-20260716163314-4b0801`

Four signed checkpoints progressed through `planned → active → review → done` with sequences
1–4. Review without a verified artifact was denied. A SuperServe sandbox checked the four-part
artifact with egress blocked, and its digest was bound into review and completion. A forged
checkpoint was ignored. A fresh process reconstructed `done`, reported the due status as
complete, excluded another tenant and prompt poison, and retained no action authority.
Organization, project, user, and negative-control containers all cleaned up.

Two initial no-write attempts failed strict model output validation. The final implementation
allows one bounded format-repair attempt but never relaxes the state, evidence, signature, or
authorization checks. This is a recovery log and briefing layer, not a lock or transactional
workflow engine.

### Genuine valid minority dissent

Final run: `dissent-council-20260716163526-04955c`

Three model families returned valid evidence-bound votes: `HOLD`, `PILOT`, and `HOLD`.
Every vote cited known evidence and supplied a falsifier. The minority `PILOT` position was
preserved in the signed proposal and recovered in a fresh process. A deliberately retrieved
poison item appeared in the input set but in none of the valid votes. Changing the evidence
digest produced `stale-evidence`; action authority remained false. Cleanup removed eight
documents and two memories.

This converts dissent from a prose aspiration into a tested invariant. It does not establish
model independence or calibration: model families may share training data and the corpus is
small.

### Resumable migration, reconciliation, and rollback

Final run: `migration-reconcile-20260716163824-2b884a`

The signed manifest contained ten records with stable custom IDs and source hashes. Initial
batch import accepted 10/10. Replaying the identical request after simulated acknowledgement
loss returned the same document IDs. A fresh process verified the separate control-container
checkpoint and reconciled exactly ten expected/imported records with no missing, duplicate, or
hash-mismatched entries.

Wrong rollback authorization was denied. The approved plan bound the exact ten IDs; bulk
deletion removed those imports, replay was denied, and a pre-existing target document remained.
The model's explanation excluded poison and selected no IDs. Final cleanup removed the
pre-existing target document plus the control records.

This demonstrates an exact-ID recovery and rollback pattern at ten records, not the documented
600-item batch boundary. File upload, 100-ID delete boundaries, partial provider failures, and
large-scale throughput remain untested.

## API and source findings

The current OpenAPI exposed 32 paths during the run. Newly wrapped exact controls include:

- `GET /v3/documents/{id}/chunks` for ordered source chunks;
- `GET /v3/documents/{id}/file-url` for a temporary signed source URL;
- `DELETE /v3/documents/bulk` for exact IDs, with a 100-ID limit in the client wrapper;
- `GET /v3/settings` for organization settings.

The hosted `GET /v3/documents/list` response used the field name `memories` for document
records. This is a contract quirk, not evidence that documents and memories are the same
resource. The field lab parses the observed shape and keeps the domain concepts separate.

The OpenAPI also exposes organization-wide bucket suggestions and model configuration. They
were inspected but not mutated because account-wide changes are outside an isolated lab run.
Current changelogs document search-latency work, memory review, Dreaming recovery changes,
forget matching, and natural-language time behavior; these are upgrade signals, not guarantees
for an account or workload. See the official [product changelog](https://supermemory.ai/changelog/)
and [API changelog](https://supermemory.ai/changelog/api/).

## Credential-loading lesson

An unsourced process inherited older Exa, Monid, and Composio environment values and received
401 responses. Running the exact campaign after sourcing the ignored `.env.local` file reached
all six acquisition channels. The client deliberately keeps normal process-environment
precedence; operators must launch live experiments from the intended secret source and record
credential provenance without recording the secret. A passing health check still says nothing
about entitlement, relevance, correctness, or future availability.

## Failures that changed the implementation

| Failure | Safe behavior | Change |
|---|---|---|
| Export parser ignored the observed document-list `memories` field | Exact erasure refused to start | Parse the observed list shape; test it explicitly |
| A memory forget call used the wrong keyword-only signature | Run stopped and cleanup executed | Match the explicit client contract; add the signature regression |
| An assertion assumed only explicit source writes become documents | No control bypass; run failed | Export actual inventory and assert named sources plus backing records |
| Unsourced subprocess used stale provider credentials | Failures remained explicit; no promotion | Source the intended ignored secret file for live runs |
| Project model output omitted exact markers | No checkpoint write | Permit one bounded repair, then retain strict validation |
| Identical instant corpora produced two then zero review candidates | No review action | Treat queue generation as asynchronous/non-deterministic |

## Confidence and remaining gaps

High confidence for the tested small synthetic cases:

- snapshot-bound export/erasure and migration rollback controls fail closed;
- direct memory creation contributes records that a complete inventory must include;
- signed checkpoint/proposal reuse can be invalidated by an exact digest change;
- valid minority dissent can survive persistence and fresh-process recovery;
- instant and dynamic Dreaming have materially different bounded readiness behavior.

Not established:

- legal/regulatory sufficiency of export, deletion, legal hold, or audit behavior;
- generated-inference approve/decline/undo end to end;
- connector, cache, backup, file, and self-hosted copies in erasure/export;
- migration at 600-document ingest or 100-ID deletion boundaries;
- model independence, decision calibration, or domain-valid project assessment;
- provider reliability or cost beyond the dated executions;
- hosted backend internals, which are not present in the public MIT-licensed client/integration
  repository.

## Verification

The complete offline suite passed **173 tests**. `compileall` and `git diff --check` also
passed. Every final live run reported successful isolated-container cleanup. No credentials,
authorization headers, real customer data, or raw run artifacts are committed.
