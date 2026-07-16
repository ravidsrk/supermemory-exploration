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

## High-value three- and four-provider systems

| Combination | Agent | Why each provider is present |
|---|---|---|
| Exa + Context.dev + OpenRouter | Company analyst | Structured baseline, broad evidence, synthesis |
| Exa + ScrapeCreators + OpenRouter | Narrative radar | Web corroboration, public conversation, analysis |
| Monid + Composio + OpenRouter | Tool architect | Paid marketplace, integration catalog, risk/cost comparison |
| SuperServe + OpenRouter + Vercel | Deployment debugger | Isolated reproduction, patch generation, live release state |
| Context.dev + Exa + ScrapeCreators + OpenRouter | Competitive intelligence | First-party, open-web, public-social, synthesis |
| Composio + SuperServe + OpenRouter | Action verifier | Authenticated tool, isolated validation, reasoning |
| Vercel + SuperServe + OpenRouter | Incident repair | Observe, reproduce, patch |
| Monid + Exa + OpenRouter | Research-tool optimizer | Compare direct search with marketplace alternatives and cost |

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

## Invalid or risky combinations

| Combination | Risk | Correction |
|---|---|---|
| Public social → static profile | Rumor becomes identity truth | Time-stamped RAG evidence; require corroboration. |
| Tool catalog → automatic execution | Ranking ignores auth and mutation risk | Inspect schema and classify side effects. |
| Generated code → unrestricted sandbox | Exfiltration and supply-chain risk | Block egress, use scoped secrets, delete sandbox. |
| Vercel state → inferred root cause | Status lacks build evidence | Fetch logs or state that cause is unknown. |
| Memory write → immediate search handoff | Eventual visibility | Use profile for direct facts or poll an indexing barrier. |
| Raw provider response → model prompt | Cost, privacy, prompt injection | Normalize, bound, mark untrusted. |

## Coverage achieved

| Provider | Authenticated live use | Combined agent |
|---|---:|---|
| Supermemory | Yes | All agents |
| OpenRouter | Yes | All reasoning paths |
| Exa | Yes | Competitive intelligence |
| Context.dev | Yes | Competitive intelligence |
| ScrapeCreators | Yes | Competitive intelligence |
| Monid | Yes | Tool selection |
| Composio | Yes | Tool selection |
| SuperServe | Yes | Sandboxed debugging |
| Vercel | Yes | Release memory |

The next valuable coverage is repeated runs, failure injection, larger eval sets, mutation
approval tests, and cost/latency tracking—not arbitrary provider subsets.
