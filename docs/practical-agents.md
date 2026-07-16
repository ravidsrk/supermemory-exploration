# Practical multi-provider agents

This chapter is the executable part of the wiki. The implementations live in
`src/supermemory_lab/advanced_agents.py`; live orchestration is in
`experiments/run_advanced_agents.py`; curated results are in
`evidence/2026-07-16-multi-provider-agents.md` and
`evidence/2026-07-16-second-pass-agents.md`. Newer agents are split into focused modules so
their safety boundary can be tested independently.

## Run them

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
python experiments/run_safe_tool_execution.py
python experiments/run_governance_scorecard.py
python experiments/run_signal_radar.py
python experiments/run_retrieval_policy_grid.py
python experiments/run_release_triage_rehearsal.py
```

Raw traces go to ignored `.runs/` files. They contain bounded experiment details but should
still be treated as private operational data. The recorder redacts credential-shaped fields
and values; it is not a general-purpose PII anonymizer.

## The placement rule

Do not put everything into one vector index. Choose the representation from the information's
lifecycle.

| Information | Supermemory representation | Why |
|---|---|---|
| Confirmed identity, policy, durable preference | Direct static memory | Profile foundation; changes rarely. |
| Incident state, active project, current plan | Direct dynamic memory | Current context that should evolve or be superseded. |
| Web page, social payload, deployment snapshot, report | Document with `taskType=superrag` | Preserve source text and provenance for RAG. |
| Complete chat turn sequence | v4 conversation | Preserve roles and conversation identity. |
| Tool output needed only inside one turn | Local trace/cache | Avoid polluting long-term memory. |
| Verified lesson from a successful action | Dynamic memory with test/evidence metadata | Transfer proven knowledge to later tasks. |
| Model speculation or unverified social claim | Do not promote to static memory | Prevent compounding hallucinations. |

## 1. Competitive-intelligence agent

Providers: Supermemory + Context.dev + Exa + ScrapeCreators + OpenRouter.

```mermaid
flowchart LR
  Q["Research question"] --> M["Recall prior intelligence"]
  Q --> B["Context.dev brand snapshot"]
  Q --> W["Exa open-web search"]
  Q --> S["Public X and Reddit signals"]
  B --> R["Supermemory RAG documents"]
  W --> R
  S --> R
  M --> L["OpenRouter synthesis"]
  B --> L
  W --> L
  S --> L
  L --> D["Dynamic conclusion memory"]
```

Use it for competitor briefs, investment watchlists, sales account research, category maps,
and recurring market digests. The split is important:

- Context.dev gives a structured first-party brand baseline.
- Exa finds broader evidence with explicit per-query cost reporting.
- ScrapeCreators supplies public social signals; those signals are noisy and temporal.
- Raw payloads remain citable RAG evidence.
- Only the analyst conclusion becomes temporal memory, with capture time and subject metadata.

Production upgrades:

- Use stable source IDs and update existing documents when a source is recrawled.
- Add claim-level corroboration: one first-party source or two independent secondary sources.
- Store a confidence and invalidation condition with every promoted conclusion.
- Diff snapshots before invoking the model; do not pay to summarize unchanged data.
- Use Context.dev monitors for high-value domains only after measuring monitor-credit economics.

## 2. Tool-selection agent

Providers: Supermemory + Monid + Composio + OpenRouter.

The agent searches two catalogs, inspects Monid candidates, falls back to a known Composio
toolkit if natural-language search returns nothing, filters for mutation risk, and remembers
the recommendation. It deliberately does not execute a candidate during discovery.

The first tool-selection run saw the decision in profile but missed it in hybrid search for
ten seconds. A later controlled matrix corrected the initial interpretation: short, medium,
and long exact canaries were visible through profile, memories, and hybrid on their first
reads. The long original natural-language tool request still missed at every tested threshold,
while exact-tail and shorter semantic queries hit. Treat this as query sensitivity, not proven
indexing lag. Use a canary/read barrier when strict read-after-write behavior matters and tune
the actual production query distribution.

Use it for agents that choose among rapidly changing integrations. Store the user intent,
side-effect class, candidate schema/auth/price, rejection reasons, selected version, expiry,
and whether execution needs human approval.

Before real execution:

1. Inspect the exact input schema and price.
2. Classify it as read, reversible write, destructive write, or external message.
3. Pin a tool version when available.
4. Dry-run or validate inputs where available.
5. Require an idempotency key for retryable writes.
6. Persist the outcome only after provider confirmation.

Monid's inspected input contract is under top-level `input` (`pathParams` and `queryParams`),
not `inputSchema`. Its nested price shape is `price.amount.value` plus currency and per-call
type. Adapters should preserve the provider schema rather than normalizing guessed fields.

## 3. Sandboxed debugging agent

Providers: Supermemory + SuperServe + OpenRouter.

This is the strongest causal experiment in the lab. Generated code ran inside an ephemeral
Firecracker-backed sandbox with all IPv4 egress denied. A verified project policy was saved
after the first patch passed. On a related hidden test, the stateless patch failed and the
patch given the remembered policy passed.

Use the pattern for code repair, dependency upgrades, organization-specific data cleaning,
migrations, incident runbooks, and review of untrusted snippets.

Safety requirements:

- Use an explicit language template; live `superserve/base` lacked `python3` despite the
  inspected OpenAPI description.
- Deny network by default and allow only required hosts.
- Never inject provider credentials as plain environment variables into generated-code sandboxes.
- Bound runtime, capture exit code separately from HTTP status, and always delete the VM.
- Persist only lessons backed by passing tests, not the model's initial theory.

## 4. Support-continuity agent

Providers: Supermemory + OpenRouter.

The agent stores verified facts in a tenant container and retrieves a combined static/dynamic
profile before answering. The live synthetic benchmark covered a maintenance window, active
project transition, and privacy policy: memory scored 3/3; empty tenants scored 0/3.

This is better than replaying every ticket:

- durable entitlements and communication preferences become static profile facts;
- open incident state and the active project become dynamic facts;
- manuals, policies, and old ticket bodies remain RAG documents;
- sensitive raw logs stay outside long-term memory unless explicitly governed;
- deletion requests map to precise forget operations in the customer's container.

Add authorization before retrieval. A container tag is an isolation primitive, not proof that
the caller may access the tenant.

## 5. Release-memory agent

Providers: Supermemory + Vercel + OpenRouter.

The implementation performs only reads: list projects and recent deployments, reduce the
response to bounded fields, distinguish observed state from unavailable root-cause evidence,
and store the snapshot as a RAG document.

Useful extensions include fetching build logs only for failures, correlating failure signatures
with verified remediation memories, versioning SLO changes, and requiring approval before any
rollback, redeploy, alias change, or production promotion.

## 6. Safe public-tool execution agent

Providers: Monid + Composio + Supermemory.

This agent closes the gap between catalog discovery and verified execution without granting
general tool authority. It executes only exact allowlisted identifiers. A Monid candidate must
inspect as `GET`, expose a numeric price under the configured cap, and return successful status.
A Composio candidate must be on the exact allowlist, report `no_auth=true`, and contain no
mutation verb token. Public outputs are stored as untrusted RAG documents; the re-inspection
policy becomes a dynamic memory.

Live result: DefiLlama's Bitcoin price endpoint executed at $0.001/call, the no-auth Hacker
News tool returned three stories, and all three Supermemory writes were accepted. This is a
read-only proof, not permission to enable arbitrary marketplace tools.

## 7. Memory-governance and injection-resistant agent

Providers: Supermemory + OpenRouter.

The 15-case scorecard covers three knowledge updates, three precise forgets with retained
controls, four isolation pairs, and five attacker-controlled documents. Every lifecycle case
checks profile, memories, and hybrid. The injection agent quotes memory as untrusted data and
can answer factual questions, but `action_authorized` is always computed as `False` in trusted
code. Even a compromised model response cannot flip it.

The live score was 15/15. All update/forget/isolation observations passed on the first read;
all malicious documents were actually retrieved, but the answers retained the SEV-2 fact,
denied action, and omitted the attacker's requested token. This is a small synthetic gate,
not proof against arbitrary prompt injection.

## 8. Longitudinal developer-signal radar

Providers: Composio Hacker News + Exa + ScrapeCreators Reddit/X + Supermemory + OpenRouter.

The fresh cycle triangulates public sources, saves each payload as RAG evidence, synthesizes
a dated briefing, and stores the conclusion as dynamic memory. The fallback cycle disables
all external providers, retrieves the prior run, and adds a deterministic application banner:
`MEMORY-ONLY FALLBACK — freshness has not been verified`.

The first live HN request used the full research question and returned zero hits. Passing a
compact source-specific query returned 6 HN hits, alongside 6 Exa, 7 Reddit, and 8 X signals.
This is why source adapters need query strategies rather than one universal prompt.

## 9. Empirically tuned recall agent

Providers: Supermemory + OpenRouter.

The policy tuner executes 120 searches: 24 combinations of memories/hybrid, threshold
0/.5/.7, rerank on/off, and rewrite on/off against three positive and two negative queries.
It ranks exact correctness, false positives, false negatives, p95 latency, response size, and
then operational simplicity. The selected policy is stored as a dated dynamic memory.

The reproducible winning run selected `memories`, threshold `.7`, rerank off, rewrite off:
4/5, zero false positives, about 658 ms median and 784 ms p95. It missed one free-form
paraphrase. A trusted domain prefix recovered the real agent question without lowering the
threshold; the final answer correctly preserved allowlist and code-level authorization rules.
Do not copy this policy to another corpus without rerunning the grid.

## 10. Release-triage rehearsal agent

Providers: Vercel + Supermemory + OpenRouter + SuperServe.

The agent reads real Vercel counts and state only, stores a bounded snapshot, retrieves a
static webhook-security runbook, and patches a deliberately broken verifier in an
egress-blocked disposable sandbox. Production observation and synthetic rehearsal carry
explicitly different labels.

The first generated patch fixed stale timestamps but still accepted future timestamps. One
test-guided repair then passed all four tests. Only the passing result became a direct lesson;
an unverified result would remain RAG failure evidence. The sandbox was deleted and no Vercel
write endpoint was called.

## Other high-value builds

| Agent | Providers | Memory design |
|---|---|---|
| Brand-change monitor | Context.dev + Supermemory + OpenRouter | Snapshot documents; dynamic change conclusions. |
| Social issue radar | ScrapeCreators + Exa + Supermemory | Public-post RAG; clustered issue memory with confidence. |
| Repository onboarding coach | Composio or Monid + Exa + Supermemory | Repo/issue documents; developer profile and learned conventions. |
| Autonomous research notebook | Exa + Context.dev + Supermemory | Source documents only; explicit analyst conclusions. |
| Incident commander | Vercel + SuperServe + Supermemory | Live state ephemeral; verified remediation becomes memory. |
| Account-planning copilot | Context.dev + Exa + public social + Supermemory | Company RAG plus time-stamped relationship memory. |
| Workflow recommender | Monid + Composio + Supermemory | Tool evaluations, auth availability, price, prior outcomes. |
| Personal operating system | Connectors + conversations + profiles | Static identity, dynamic goals, RAG source library. |
| Developer-signal radar | Composio + Exa + public social + Supermemory | Source RAG, dated conclusions, stale fallback banner. |
| Release-triage rehearsal | Vercel + SuperServe + OpenRouter + Supermemory | Read-only state, static runbook, test-verified lesson. |
| Retrieval-policy tuner | Supermemory + OpenRouter | Dated policy benchmark; trusted query template. |

## What not to build

- A universal “remember everything” container shared by all users and agents.
- A loop that writes its own generated answer as truth on every turn.
- An immediate handoff that assumes write acknowledgement means search visibility.
- A tool agent that treats catalog ranking as a safety or quality score.
- A social agent that promotes a single post into a durable fact.
- A production debugger that runs generated code on the host or with unrestricted egress.
