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

## Coverage achieved

| Provider | Authenticated live use | Combined agent |
|---|---:|---|
| Supermemory | Yes | All agents |
| OpenRouter | Yes | All reasoning paths |
| Exa | Yes | Intelligence; signal radar; corroboration; dependency guardian |
| Context.dev | Yes, including current GET scrape | Intelligence; monitor; corroboration |
| ScrapeCreators | Yes | Intelligence; signal radar; corroboration |
| Monid | Yes, including priced GET execution | Tool selection; safe public runner; dependency guardian |
| Composio | Yes, including no-auth execution | Tool selection; safe public runner; signal radar; dependency guardian |
| SuperServe | Yes | Sandboxed debugging; release triage; dependency guardian |
| Vercel | Yes, read-only | Release memory; release-triage rehearsal |

Repeated runs, failure injection, lifecycle controls, a 120-search policy grid, multi-scope
credentials, natural-time queries, and learned model fallbacks are now in the lab. The next
valuable coverage is a reviewed reversible-write approval test, connector sync/update/delete
on an entitled plan, larger blinded datasets, and sustained cost/latency tracking—not arbitrary
provider subsets.
