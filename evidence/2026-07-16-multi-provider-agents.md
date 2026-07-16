# Multi-provider agent evidence — 2026-07-16

This is a curated, secret-free summary of live runs. Raw traces are ignored under `.runs/`.
No Vercel project names, public-post bodies, account identifiers, credentials, sandbox access
tokens, or Supermemory container IDs are committed.

## Credential and entitlement smoke test

All supplied services returned an authenticated HTTP 200 on a minimal read-only or catalog
operation: Supermemory, OpenRouter, Exa, Context.dev, ScrapeCreators, Monid, Composio,
SuperServe, and Vercel. Context.dev's current base URL includes `/v1`.

## Competitive-intelligence agent

| Step | Observed result |
|---|---|
| Prior Supermemory recall | 0 results in a fresh isolated workspace. |
| Context.dev | Retrieved the expected brand. |
| Exa | 6 results; reported cost was $0.007. |
| ScrapeCreators | Public X timeline and Reddit search both succeeded. |
| Persistence | 4 raw evidence records accepted as `superrag` documents. |
| Synthesis | OpenRouter produced a 4,840-character sourced brief. |
| Temporal memory | The conclusion was accepted as a dynamic memory. |

The agent used five providers in one run. Raw payloads were treated as untrusted evidence,
not as executable instructions.

## Tool-selection agent

| Step | Observed result |
|---|---|
| Monid discovery | 5 candidates. |
| Monid inspection | Top 2 candidates inspected; later inspection confirmed the schema is under top-level `input`, not `inputSchema`, and price is nested under `price.amount.value`. |
| Composio natural-language query | 0 tools. |
| Composio toolkit fallback | 12 GitHub tools. Early catalog order was dominated by mutation tools, so mutation-risk filtering is mandatory. |
| Immediate profile visibility | 1 dynamic decision appeared on the first poll, ~1.1 seconds client wall. |
| Immediate hybrid search | Still returned no result inside a separate 10-second window. |
| Memory-only follow-up | Profile context was available without another Monid or Composio call. |

Correction from the second pass: this did **not** prove indexing lag. Exact canaries in short,
medium, and long direct memories were visible through profile, memories, and hybrid on the
first read. The long natural-language request still missed while shorter/exact queries hit,
which points to query sensitivity. Immediate handoffs should use a canary barrier and evaluate
the production query separately.

## Sandboxed debugging agent

The sandbox used the explicit `superserve/python-3.11` template, denied all IPv4 egress, and
was deleted after the run.

| Trial | Result |
|---|---|
| Original buggy normalizer | Failed its project-policy test. |
| Generated patch with policy | Passed. |
| Related transfer task without memory | Failed the hidden test; it missed Unicode NFKC, internal-space collapse, and stable deduplication. |
| Related transfer task with verified Supermemory lesson | Passed the same hidden test. |
| Lesson visibility | Dynamic profile appeared on the first poll. |
| Cleanup | Sandbox deletion succeeded. |

The first attempt used `superserve/base`; live execution returned `python3: not found`, despite
the inspected OpenAPI description saying the base template includes Python 3.12. Selecting the
explicit Python template fixed the experiment. Treat template contents as runtime capabilities,
not documentation guarantees.

## Support-continuity benchmark

Three isolated synthetic tenants covered a maintenance window, a project transition, and a
privacy-safe diagnostics policy. Each memory-backed answer was paired with the same model and
question in an empty tenant.

| Condition | Exact rubric passes |
|---|---:|
| Empty-tenant baseline | 0 / 3 |
| Supermemory profile context | 3 / 3 |

All three seeded facts were profile-visible on the first poll. The benchmark is small and
synthetic, but it demonstrates tenant isolation, static/dynamic placement, and an information
advantage that the stateless model did not have.

## Read-only release-memory agent

- Vercel returned 20 projects and 30 recent deployments.
- The agent separated observed state from root causes that would require logs.
- A bounded, read-only snapshot was accepted as a Supermemory RAG document.
- Project names and deployment details remain only in the ignored local trace and the user's
  own memory workspace.

## Scope and limitations

- These are contract and causal probes, not load tests or statistically powered benchmarks.
- Public social data is a noisy signal and must never be promoted to a stable fact without
  corroboration.
- No Composio or Monid mutation tool was executed. A later pass executed one exact-allowlisted
  read-only tool from each provider after method/auth/price checks.
- The support result needs a larger, blinded dataset before it can support a production KPI.
