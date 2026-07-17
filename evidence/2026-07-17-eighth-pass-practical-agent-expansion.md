# Eighth-pass practical agent expansion — 2026-07-17

## Research question

Which weakly tested Supermemory surfaces and provider combinations can become genuinely new,
production-shaped agents rather than minor variants—and which safety properties survive real
hosted execution, process restart, prompt injection, authorization mismatch, replay, scope
violation, revocation, rate limiting, and provider-contract drift?

## Executive summary

Six new implementations and live experiments passed. They extend the field lab from 41 to 47
reference implementations and from 173 to 208 package-aware offline tests.

| Agent | Primary capability under test | Final secret-safe run | Result |
|---|---|---|---|
| Meeting commitment steward | Multipart file, chunks, temporary URL, temporal write | `meeting-commitments-20260717014432-04c289` | Passed |
| Consent-aware intake firewall | Purpose/sensitivity/retention-bound write | `intake-firewall-20260717014812-1dc5ac` | Passed |
| Tool apprentice | Episodic evidence → verified reusable procedure | `tool-apprentice-20260717015304-1644e9` | Passed |
| Memory quality auditor | Inventory-wide contamination detection/quarantine | `quality-audit-20260717015640-846d95` | Passed |
| Least-privilege worker | Scoped key, revocation, rate limit, signed receipt | `least-privilege-worker-20260717020107-58d1bc` | Passed |
| All-provider readiness commander | 255-subset map, 28-pair portfolio, all credentials | `all-provider-readiness-20260717020711-0d7c08` | Passed |

The main design conclusion is stronger than “memory improves answers.” Supermemory is most
useful as a governed state plane: source archive, signed checkpoint ancestry, scoped recall,
temporal memory, and reviewable evidence. Consent, action permission, exact mutation sets,
trusted control envelopes, replay state, and canonical workflow truth still belong in
deterministic application or transactional state.

## Current product and source recheck

The official hosted OpenAPI still exposed 32 paths. Current material surfaces included file,
batch and ordinary document ingestion; chunks and temporary file URLs; exact memory CRUD and
history; profiles and buckets; connection lifecycle; scoped keys; container settings and
merge; and Dreaming/inferred review. The public monorepo was inspected at
[`8d926332ab23aa5785def636aca9d0a52fea4a65`](https://github.com/supermemoryai/supermemory/tree/8d926332ab23aa5785def636aca9d0a52fea4a65),
with 1,014 tracked files in the local inspection clone.

The official [add-memory guide](https://supermemory.ai/docs/add-memories) documents file
ingestion up to 50 MB and its task, entity, metadata, filter, and Dreaming controls. The
[authentication guide](https://supermemory.ai/docs/authentication) documents scoped expiry,
endpoint restriction, a default 500 requests per 60 seconds, a 1–10,000 request range, a
1–3,600,000 ms window, and immediate revocation. Current
[API changelog](https://supermemory.ai/changelog/api/) entries describe signed file URLs that
expire after 24 hours, export limits/expiry, explicit `429` plus `Retry-After`, filtered
writes, Dreaming changes, review, and natural-time behavior.

The GitHub API exposed 27 current open issue reports during the recheck. They are signals, not
reproduced failures. Relevant reports include self-hosted macOS process wedging
[#1296](https://github.com/supermemoryai/supermemory/issues/1296), profile-bucket migration
[#1293](https://github.com/supermemoryai/supermemory/issues/1293), middleware outage behavior
[#1287](https://github.com/supermemoryai/supermemory/issues/1287), Python SDK result/dedup
parsing [#1266](https://github.com/supermemoryai/supermemory/issues/1266), integration-version
drift [#1247](https://github.com/supermemoryai/supermemory/issues/1247), MCP graph scope
[#1246](https://github.com/supermemoryai/supermemory/issues/1246), and middleware default/docs
drift [#1241](https://github.com/supermemoryai/supermemory/issues/1241).

Official social activity remains useful only as product-direction evidence. The
[Supermemory X account](https://x.com/supermemory) and its
[Mastra integration announcement](https://x.com/supermemory/status/2020959115854610629)
support ecosystem momentum; neither establishes reliability or independent adoption.

## 1. Uploaded-meeting commitment steward

Implementation:
[`commitment_steward.py`](../src/supermemory_lab/commitment_steward.py) and
[`run_meeting_commitment_steward.py`](../experiments/run_meeting_commitment_steward.py).

The experiment uploaded an actual Markdown artifact through multipart ingestion, waited for
processing, read its ordered source chunks, and requested its temporary file URL. The URL was
validated as HTTPS but never stored in the trace, memory, or model prompt. The model could
propose a commitment only in exact `{owner} will <action> by YYYY-MM-DD` form with an exact
chunk quote. Trusted code checked owner, date window, citation, signed plan, exact approval,
and replay before writing direct temporal memories.

Observed final behavior:

- one ordered chunk contained both synthetic commitments;
- exactly two candidates—Asha due 2026-08-03 and Ravi due 2026-08-05—passed quote and source
  checks;
- the planted instruction was absent from candidates and final due brief;
- wrong authorization and approval replay were denied;
- both commitments became searchable and a fresh process cited every created ID;
- the other tenant stayed absent, action authority stayed false, and all three synthetic
  containers/resources were removed.

Practical uses include meeting follow-up, contract-obligation review, support escalation, and
project governance. Do not treat extraction as commitment creation: a human or canonical
system must own acceptance and changes.

## 2. Consent-aware memory intake firewall

Implementation:
[`intake_firewall.py`](../src/supermemory_lab/intake_firewall.py) and
[`run_memory_intake_firewall.py`](../experiments/run_memory_intake_firewall.py).

The firewall signs subject, purpose, allowed categories, expiry, retention ceiling, and static
permission. Each intake request separately declares save intent, durability, provenance,
sensitivity, and retention. Deterministic policy owns secret patterns, purpose mismatch,
retention, and restricted categories; OpenRouter supplies only a bounded advisory label.

Observed final behavior:

- one explicit preference was accepted as expiring dynamic memory;
- one consented conversation was stored as a purpose-filtered document;
- a synthetic credential was denied; health and implicit inference required review; advertising
  purpose expansion was denied;
- denied content never reached subject or other-tenant memory;
- wrong authorization and replay were denied;
- inventory exposed the safe memory's expiry and cleanup removed all synthetic state.

This is the recommended production write boundary. “User said it” and “model inferred it” are
not sufficient consent or retention policy.

## 3. Episodic-to-procedural tool apprentice

Implementation:
[`tool_apprentice.py`](../src/supermemory_lab/tool_apprentice.py) and
[`run_tool_apprenticeship_agent.py`](../experiments/run_tool_apprenticeship_agent.py).

The agent inspected and executed a priced Monid public Hacker News GET route and an exact
Composio no-auth read route, normalized outcomes, signed both episodes, and verified the
candidate procedure with 4/4 checks in an egress-denied Python sandbox. Only the exact signed
candidate could be promoted; a fresh loader ignored unsigned memory and revalidated the
current contracts before permitting execution.

Observed final behavior:

- Monid returned eight items with six relevant; Composio returned eight of eight relevant;
- both episodes and the promoted skill were signature-valid;
- wrong approval and replay were denied;
- unsigned poison was ignored;
- current contracts kept the skill executable, while simulated method drift disabled it;
- no external action authority was created and all sandbox/memory resources were removed.

The first sandbox attempt failed safely with HTTP `400` because its network object did not
match the current SuperServe contract. No sandbox proof or skill was created. The final run
used the explicit Python 3.11 template and deny-all IPv4 egress shape.

## 4. Memory contamination and quality auditor

Implementation:
[`quality_auditor.py`](../src/supermemory_lab/quality_auditor.py) and
[`run_memory_quality_auditor.py`](../experiments/run_memory_quality_auditor.py).

The auditor enumerates actual provider document/memory inventories and hashes raw content
before model exposure. Deterministic rules cover secret-like values, instruction injection,
missing provenance, orphan source, unreviewed inference, expired-but-visible records,
malformed expiry, duplicates, and canonical-key contradiction. The signed snapshot contains
rule findings and hashes—not raw secret text. Only exact secret/injection IDs may be
quarantined automatically; contradictions remain review work.

Observed final behavior:

- initial findings included canonical contradiction, injection, missing provenance, and
  secret classes;
- sensitive raw content was absent from both snapshot and explanation;
- drift, safe-record quarantine, wrong authorization, and replay were denied;
- exactly the two critical records were quarantined;
- the safe and conflicting records remained, the contradiction remained reviewable, and the
  other tenant stayed absent.

This pattern should run before personalization or autonomous planning reads, but quarantine
must not become a universal model-controlled delete path.

## 5. Least-privilege delegated memory worker

Implementation:
[`delegated_worker.py`](../src/supermemory_lab/delegated_worker.py) and
[`run_least_privilege_worker.py`](../experiments/run_least_privilege_worker.py).

The manifest signs one task ID, one container, one query, one expected marker, two operations,
one context ceiling, and expiry. A newly issued hosted credential was provided only to the
worker client. It could search the allowed memory and write one receipt; the model received no
tool, deployment, messaging, or other-tenant authority.

Observed final behavior:

- cross-container search returned `403`;
- cross-container memory creation returned `403`;
- wrong task authorization and replay were denied;
- the result contained task, result, and no-action markers, retained the approved `HOLD`
  control, omitted poison/denied-tenant content, and produced a verifiable receipt;
- immediately after revocation the allowed search returned `401`;
- a separate key capped at two requests produced exactly `[200, 200, 429]`, and the HTTP
  transport preserved a non-empty `Retry-After` header;
- all keys were revoked and both containers removed.

The authentication prose currently emphasizes a singular container while a prior hosted lab
run observed a multi-container key response. That is a docs/contract tension, not permission
to broaden worker scope. Prefer one task, one container, one short expiry.

## 6. Provider permutation map and all-provider commander

Implementation:
[`provider_permutations.py`](../src/supermemory_lab/provider_permutations.py) and
[`run_all_provider_readiness_commander.py`](../experiments/run_all_provider_readiness_commander.py).

The map treats Supermemory as the constant state plane and enumerates every non-empty subset
of the eight auxiliary providers: `2^8 - 1 = 255`. Each subset gets roles, viable archetypes,
required controls, reasoning/current-state/isolated-code flags, and an external-action-surface
flag. This is exhaustive design classification, not 255 claimed live workflows.

The existing live portfolio was then analyzed pairwise. It covered 24 of 28 possible provider
pairs. Missing were:

1. ScrapeCreators + SuperServe;
2. ScrapeCreators + Vercel;
3. Monid + Vercel;
4. Composio + Vercel.

The final all-provider run exercised:

- Context.dev official product-page retrieval;
- Exa primary-domain web search with five results;
- ScrapeCreators official public X retrieval with nine bounded records;
- Monid discovery with six candidate tools and no execution;
- Composio inspection of the pinned `HACKERNEWS_SEARCH_POSTS` no-auth contract and no
  execution;
- Vercel read-only identity verification with no identity field persisted;
- SuperServe egress-denied manifest hashing with exact output and sandbox deletion;
- OpenRouter synthesis inside an application-owned control envelope;
- Supermemory prior-context hashing, signed snapshot ancestry, and one exactly authorized
  report write.

All seven non-model observations succeeded. The report cited all seven IDs, stayed `REVIEW`,
excluded the planted prior instruction, denied wrong authorization and replay, and authorized
no external action. The live portfolio therefore has an exercised workflow covering every one
of the 28 provider pairs.

The first all-provider run failed safely. A broad Composio query returned zero exact tools,
then OpenRouter omitted required markers even after one repair. Nothing was persisted. The
final design inspects an exact known read contract and makes `CAMPAIGN`, `DECISION`, `CITE`,
and `NO_EXTERNAL_ACTION` fields deterministic application output. The model supplies analysis
prose inside that envelope and cannot format away governance.

## Contradictions and gaps

1. **255 classified is not 255 live-tested.** Every subset is mapped; every pair appears in a
   live workflow; higher-order ordering, simultaneous degradation, latency, and economics are
   still untested.
2. **Scoped-key prose and hosted breadth differ.** Current docs describe a singular container;
   an earlier run observed three tags. Use least privilege and contract-test the exact account.
3. **File path passed, size boundary did not.** Markdown multipart/chunks/temporary URL passed;
   exact 50 MB rejection and other formats remain open.
4. **Temporary links are capabilities.** Official changelog says file URLs expire after 24
   hours. The lab validated presence, not expiry, and deliberately never persisted the URL.
5. **Quality rules are high-precision, not completeness proof.** Hash-safe deterministic rules
   caught the planted cases; they do not prove all PII, secrets, contradictions, or provenance
   defects are detectable.
6. **Tool skill evidence is narrow.** Two equivalent public-read routes and one isolated
   verifier passed. Mutation tools, OAuth, retries, provider outage, and real-world side effects
   require separate authorization and evaluation.
7. **Issue reports remain reported.** Twenty-seven open reports guide regression tests but were
   not reproduced merely because their titles or bodies exist.
8. **Hosted internals remain opaque.** The MIT monorepo exposes clients, integrations, apps,
   docs, MCP, and local components, not the hosted extraction/search implementation.

## Six-month operational recommendations

1. Put the intake firewall in front of every automatic memory write before expanding agents.
2. Issue short-lived, single-container credentials to sandboxes and delegated workers; alert on
   unexpected `403`, `401`, or missing `Retry-After` behavior.
3. Run contamination audits on a schedule and before high-consequence personalized planning;
   keep contradictions in review rather than deleting them automatically.
4. Store source identity, capture time, upstream publisher, evidence class, and invalidation
   condition with every durable conclusion.
5. Promote tool procedures only from signed successful episodes plus isolated verification;
   re-inspect method/schema/auth/version/cost before each execution cycle.
6. Keep trusted control envelopes, authorization, replay ledgers, legal holds, workflow state,
   and external audit outside model-authored text.
7. Retest the 32-path OpenAPI digest, scoped controls, file/chunk contract, contamination suite,
   and all-provider healthy/degraded matrix monthly.
8. Next prioritize connector lifecycle on an entitled plan, a qualifying multi-parent
   inference review, exact file/cardinality boundaries, higher-order provider degradation,
   self-hosted upgrade/restore, and a 100+ case blinded domain benchmark.

## Verification

```text
PYTHONPATH=src python3 -m unittest -q
Ran 208 tests in 0.034s
OK
```

The secret-fingerprint audit found no supplied credential fragments outside ignored local
configuration and ignored raw-run storage. Every final live experiment deleted its synthetic
Supermemory containers; sandboxed experiments deleted their VMs; the delegated-worker run
revoked both scoped keys. Raw traces remain ignored under `.runs/`.

## Primary sources

- [Supermemory documentation](https://supermemory.ai/docs/intro)
- [Add memories and files](https://supermemory.ai/docs/add-memories)
- [Authentication and scoped keys](https://supermemory.ai/docs/authentication)
- [Hosted OpenAPI](https://api.supermemory.ai/v3/openapi)
- [API changelog](https://supermemory.ai/changelog/api/)
- [Product changelog](https://supermemory.ai/changelog/)
- [MIT-licensed Supermemory monorepo](https://github.com/supermemoryai/supermemory)
- [Official X account](https://x.com/supermemory)
- [MemoryBench](https://github.com/supermemoryai/memorybench)
