# Provider combination map

Supermemory is the state plane in these patterns. Other providers supply evidence, reasoning,
tools, execution, or operational state. There are 256 mathematical subsets of the eight
auxiliary providers and many more execution orders; enumerating them is not useful. This map
covers combinations with distinct production value and calls out invalid ones.

## Provider roles

| Provider | Primary role | Durable output worth remembering | Keep ephemeral |
|---|---|---|---|
| OpenRouter | Reasoning and synthesis | Verified conclusion, decision, lesson | Chain-of-thought, raw prompt, failed speculation |
| Exa | Open-web discovery | Source document and provenance | Duplicate result wrappers |
| Context.dev | Structured company/web intelligence | Brand snapshot, monitored change | Rendering noise and transient scrape metadata |
| ScrapeCreators | Public social/platform data | Time-stamped source evidence | Counters unless the use case needs trends |
| Monid | Dynamic paid-tool discovery | Tool evaluation, price/schema snapshot | Catalog search noise |
| Composio | Tool catalog, auth, execution | Tool outcome and version | OAuth token, full auth response |
| SuperServe | Isolated compute | Passing-test lesson, artifact digest | Access token, transient stdout, failed code |
| Vercel | Deployment state | Release snapshot, verified failure signature | Tokens, unrelated project metadata |

## Valuable pairings with Supermemory

| Pair | Practical use | Retrieval mode |
|---|---|---|
| + OpenRouter | Personalized, support, and decision agents | Profile foundation; hybrid specifics |
| + Exa | Research agent with durable sources | Hybrid documents |
| + Context.dev | Company and brand memory | Profile confirmed facts; documents snapshots |
| + ScrapeCreators | Social trend memory | Hybrid documents with recency metadata |
| + Monid | Cost-aware dynamic tool chooser | Profile for recent decisions |
| + Composio | Authenticated action agent | Profile preferences; exact outcome memories |
| + SuperServe | Safe code/data agent | Profile for verified project rules |
| + Vercel | Release and incident memory | Hybrid snapshot history |
| + OpenRouter model ensemble | Cross-process adaptive routing | Dynamic policy and verified failure outcomes |

## High-value three- and four-provider systems

| Combination | Agent | Why each provider is present |
|---|---|---|
| Exa + Context.dev + OpenRouter | Company analyst | Structured baseline, broad evidence, synthesis |
| Exa + ScrapeCreators + OpenRouter | Narrative radar | Web corroboration, public conversation, analysis |
| Monid + Composio + OpenRouter | Tool architect | Paid marketplace, integration catalog, risk/cost comparison |
| Monid + Composio | Safe public-tool runner | Price/schema inspection, no-auth read execution, outcome evidence |
| SuperServe + OpenRouter + Vercel | Deployment debugger | Isolated reproduction, patch generation, live release state |
| Context.dev + Exa + ScrapeCreators + OpenRouter | Competitive intelligence | First-party, open-web, public-social, synthesis |
| Composio + SuperServe + OpenRouter | Action verifier | Authenticated tool, isolated validation, reasoning |
| Vercel + SuperServe + OpenRouter | Incident repair | Observe, reproduce, patch |
| Monid + Exa + OpenRouter | Research-tool optimizer | Compare direct search with marketplace alternatives and cost |
| Composio + Exa + ScrapeCreators + OpenRouter | Developer-signal radar | HN, open web, Reddit/X, synthesis and fallback history |
| Context.dev + Exa + ScrapeCreators + OpenRouter | Corroboration council | Official scrape, web discovery, public signals, claim synthesis |
| Monid + Exa + Composio + SuperServe + OpenRouter | Dependency-risk guardian | Exact-version CVE lookup, official evidence, HN, isolated smoke test, synthesis |
| Context.dev + Exa + ScrapeCreators + OpenRouter | Relationship account brief | Company baseline, open-web change, public signals, cited synthesis; CRM consent remains separate |
| Vercel + Exa + SuperServe + OpenRouter | Incident forensics | Read-only state, official guidance, isolated falsification, uncertainty-aware synthesis |
| Monid + Composio + Exa + OpenRouter | Tool-economics portfolio | Priced catalog route, integration route, direct-search route, comparable decision |
| Three OpenRouter model families | Evidence-bound decision council | Independent votes, strict citations, falsifiers, dissent, stale-evidence proposal |
| OpenRouter + SuperServe | Adaptive tutor | Personalized teaching plus isolated deterministic assessment; model never grades |
| Context.dev + Exa + ScrapeCreators + Monid + Composio + OpenRouter | Budgeted due diligence | Structured/web/social/tool evidence, publisher diversity, resumable partial-state research |
| Vercel + Context.dev + SuperServe + OpenRouter | Change-risk board | Minimized live health, official rollout guidance, isolated rehearsal, deterministic hold |

Add Supermemory to each row for longitudinal state, provenance, tenant isolation, and future
retrieval.

## Order matters

| Workflow | Correct order | Reason |
|---|---|---|
| Research | Recall → fetch → corroborate → synthesize → persist | Avoid stale repetition while preserving fresh evidence. |
| Tool use | Recall → discover → inspect → approve → execute → verify → persist | A catalog hit is not authorization. |
| Debugging | Recall policy → reproduce → patch → test → persist lesson | Never store an untested theory. |
| Release ops | Recall signatures → read state → fetch logs → analyze → approve mutation | Separate observation from action. |
| Support | Authorize tenant → profile → targeted search → answer → store update | Prevent cross-tenant leakage. |
| Enterprise context | Resolve allowed scopes → retrieve separately → apply precedence → answer → authorize in code | Context composition must not weaken policy. |
| Model routing | Recall policy → validate freshness/task family → call → contract-check → fallback → persist outcome | Old benchmark memory is not a runtime guarantee. |
| Dependency risk | Read exact version → inspect tool → fetch evidence → isolate test → human approval → persist lesson | A zero-CVE response cannot authorize production change. |
| Memory correction | Retrieve evidence → quarantine/gate → propose exact hash → human approve → update once → verify latest | Model explanation and graph context are not approval authority. |
| Multi-agent recovery | Read candidates → verify signature/chain → resume one transition → contract-check → checkpoint → reconcile | Semantic memory is a recovery log, not a transactional workflow engine. |
| Account briefing | Authorize private scope → recall CRM → verify readiness → fetch public evidence → cite → deny outreach by default | Public interest and relationship history do not create contact consent. |
| Incident forensics | Read live state → retrieve prior lessons → acquire logs/evidence → falsify in isolation → state unknown or supported → approve separately | A rehearsal is not a production diagnosis. |
| Tool economics | Recall unexpired policy → rediscover/reinspect → execute comparable reads → validate → rank known costs → persist outcome | Unknown price cannot be treated as free. |
| Decision council | Freeze evidence manifest → independent blind votes → schema/citation/falsifier validation → preserve dissent → propose → recheck digest | Model majority is neither truth nor action authority. |
| Adaptive tutoring | Verify signed mastery → decay/schedule → teach → assess outside model → verify → version mastery | A persuasive lesson is not evidence of learning. |
| Due diligence | Resume signed ledger → acquire within budget → normalize publisher/source → cite → label degradation → promote only if complete | Fluent partial research must not masquerade as a complete decision. |
| Change risk | Minimize live state → obtain current guidance → rehearse in isolation → apply deterministic health gate → human review | A passing rehearsal cannot override unhealthy production state. |
| Retention | Inventory exact IDs → partition policy → place/verify holds → regenerate drifted plan → exact approve → forget → verify → external audit | A model must never select deletion IDs or own the only audit record. |

## Permutation coverage lattice

The useful design space is defined by the role memory plays, not by every mathematical subset
of providers.

| Memory role | Fresh evidence | Reasoning | External action | Executed pattern | Required gate |
|---|---|---|---|---|---|
| Profile foundation | None | OpenRouter | None | Support continuity; preference evolution | Tenant authorization and correction UX |
| Hierarchical context | None | OpenRouter | Proposed only | Enterprise context composer | Trusted scope precedence and action policy |
| Source archive | Exa / Context.dev / social | OpenRouter | None | Intelligence and signal radar | Provenance, recency, bounded context |
| Claim promotion | Official + independent channels | OpenRouter | Durable memory write | Corroboration council | Minimum support, official source, conflict veto |
| Tool policy | Monid / Composio catalogs | OpenRouter optional | Read-only tool | Tool selector and safe public runner | Exact allowlist, schema, method, price, result validation |
| Verified execution lesson | Live state / generated patch | OpenRouter | Sandboxed test | Debug and release rehearsal | Egress block, tests, deletion, write only after pass |
| Adaptive control policy | OpenRouter catalog and outcomes | Candidate models | Model call + bounded fallback | Self-repairing model router | Holdout contract, expiry, fallback, total economics |
| Temporal retrieval | Dated direct facts | OpenRouter | None | Temporal agenda | Trusted clock/timezone and answer window |
| Risk recommendation | Monid + Exa + Composio | OpenRouter | Sandbox only | Dependency-risk guardian | Exact installed version, evidence diversity, human change owner |
| Governed correction | Canonical + untrusted candidate sources | OpenRouter explanation only | Versioned memory update | Memory curator | Source/freshness gate, exact hash approval, replay ledger |
| Recovery checkpoint | Signed prior agent output | OpenRouter | Direct checkpoint write | Resumable workcell | Signature, predecessor, state machine, output contract, DB reconciliation |
| Relationship intelligence | CRM + Context.dev + Exa + social | OpenRouter | Brief only | Account briefing | Consent, exact readiness, citations, stale banner, outreach denial |
| Incident learning | Vercel + official web + sandbox | OpenRouter | Sandbox only | Hypothesis forensics | Provenance class, logs-or-unknown, hypothesis falsification, human mitigation |
| Tool portfolio | Monid + Composio + Exa | OpenRouter optional | Read-only tools | Economics router | Comparable task, unknown-cost shadow, expiry, route revalidation |
| Evidence deliberation | Immutable source manifest | Multiple model families | Proposal only | Decision council | Strict citations/falsifiers, quorum, dissent, digest freshness, external authority |
| Verified mastery | Signed assessment history | OpenRouter | Egress-blocked grader | Adaptive tutor | Signature, deterministic decay, verified grade, versioned update |
| Resumable research | Official/web/social/tool sources | OpenRouter | Read-only acquisition | Due-diligence campaign | Call/cost budget, publisher diversity, checkpoint integrity, degraded-state refusal |
| Change simulation | Vercel + official guidance | OpenRouter | Egress-blocked rehearsal | Change-risk board | Minimized state, evidence classes, live health override, stale advice |
| Retention governance | Exact latest inventory | OpenRouter explanation only | Exact forget | Retention controller | Legal hold, plan digest, drift/replay denial, absence check, external audit |

## Invalid or risky combinations

| Combination | Risk | Correction |
|---|---|---|
| Public social → static profile | Rumor becomes identity truth | Time-stamped RAG evidence; require corroboration. |
| Tool catalog → automatic execution | Ranking ignores auth and mutation risk | Inspect schema and classify side effects. |
| Generated code → unrestricted sandbox | Exfiltration and supply-chain risk | Block egress, use scoped secrets, delete sandbox. |
| Vercel state → inferred root cause | Status lacks build evidence | Fetch logs or state that cause is unknown. |
| Memory write → unchecked immediate handoff | Query miss can look like indexing lag | Poll an exact canary, then separately evaluate the real query. |
| Raw provider response → model prompt | Cost, privacy, prompt injection | Normalize, bound, mark untrusted. |
| Calibration winner → unconditional route | Task drift creates silent failures | Validate output, fall back, record outcome, expire policy. |
| Several APIs → “independent corroboration” | Providers may repeat one publisher | Store upstream publisher and claim-level support graph. |
| Multi-scope retrieval → model authorization | Lower-precedence memory can override policy | Resolve hierarchy and action permission in trusted code. |
| Dynamic batch completion → synchronous readiness | Document completion can precede distilled-memory visibility | Poll the exact next read; directly write confirmed normalized facts on timeout. |
| Signed checkpoint → trusted truth | Integrity does not establish correctness | Verify artifacts/evidence and keep transitions in a workflow ledger. |
| Unknown catalog cost → zero-cost route | Missing economics wins falsely | Shadow until costs are comparable; record date and charge semantics. |
| Model plurality → authorized decision | Shared bias or repeated source becomes authority | Require evidence-bound votes and external decision ownership. |
| Teaching model → mastery score | Same model can reward its own explanation | Grade from independently verified evidence and sign the result. |
| Passing rehearsal → deploy | Synthetic mechanism does not establish live safety | Apply current health/SLO gates and require explicit change approval. |
| Semantic deletion → legal retention execution | Probabilistic selection can miss or over-delete | Resolve exact IDs, legal holds, plan digest, replay ledger, and external audit. |

## Coverage achieved

| Provider | Authenticated live use | Combined agent |
|---|---:|---|
| Supermemory | Yes | All agents |
| OpenRouter | Yes | All reasoning paths |
| Exa | Yes | Intelligence; signal radar; corroboration; dependency guardian; account brief; incident forensics; tool portfolio |
| Context.dev | Yes, including current GET scrape | Intelligence; monitor; corroboration; account brief |
| ScrapeCreators | Yes | Intelligence; signal radar; corroboration; account brief |
| Monid | Yes, including priced GET execution | Tool selection; safe public runner; dependency guardian; tool portfolio |
| Composio | Yes, including no-auth execution | Tool selection; safe public runner; signal radar; dependency guardian; tool portfolio |
| SuperServe | Yes | Sandboxed debugging; release triage; dependency guardian; incident forensics |
| Vercel | Yes, read-only | Release memory; release-triage rehearsal; incident forensics |

The sixth due-diligence run also exercised current credential degradation: Exa, Monid, and
Composio returned 401 after authenticating in earlier passes. The agent retained their failures,
continued with three healthy publisher channels, labeled the report partial, and withheld
promotion. “Yes” in the table records successful live use in this lab, not current credential
health or an availability guarantee.

Repeated runs, failure injection, lifecycle controls, a 120-search policy grid, multi-scope
credentials, natural-time queries, learned model fallbacks, signed restart recovery, batch
readiness fallback, abstaining incident analysis, and cross-tool economics are now in the lab.
The next valuable coverage is a reviewed reversible-write approval test, connector
sync/update/delete on an entitled plan, refreshed-provider full/degraded campaigns, larger
blinded datasets, and sustained cost/latency tracking—not arbitrary provider subsets.
