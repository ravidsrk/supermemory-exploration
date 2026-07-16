# Supermemory Field Lab

An evidence-driven field lab for exploring [Supermemory](https://supermemory.ai) as a production memory layer for AI agents.

Primary docs entrypoint: [https://supermemory.ai/docs/intro](https://supermemory.ai/docs/intro)

This repository deliberately separates four kinds of knowledge:

- **Documented** — behavior stated by official documentation.
- **Source-inspected** — behavior visible in public repositories and SDKs.
- **Observed** — behavior reproduced against the hosted API.
- **Inferred** — architecture or product conclusions that still need validation.

## What this repo is for

Hands-on exploration of Supermemory product surface, APIs, SDKs, and integration patterns:

- Reproducible probes for ingestion, search, profiles, updates, isolation, and lifecycle behavior.
- Working agent patterns, with fake-backed unit tests and opt-in live tests.
- A practical wiki of capabilities, tradeoffs, failure modes, and design guidance.
- A six-month experiment roadmap that can evolve with the product.

## Status

Active research. The initial harness and evidence catalog are being built now.

## Repository map

| Path | Purpose |
|---|---|
| `docs/` | Durable practical wiki and research synthesis |
| `src/` | Reusable Supermemory client and agent patterns |
| `experiments/` | Reproducible live probes and evaluations |
| `tests/` | Offline contract and architecture tests |
| `evidence/` | Curated, secret-free observations from live runs |

## Primary sources

| Area | URL |
|---|---|
| Intro | https://supermemory.ai/docs/intro |
| Docs home | https://supermemory.ai/docs |
| Open-source monorepo | https://github.com/supermemoryai/supermemory |
| MemoryBench | https://github.com/supermemoryai/memorybench |

## Secret safety

Copy `.env.example` to `.env.local` and fill only the keys needed by a specific experiment. All `.env*` files except the example are ignored. Scripts must redact authorization headers and never serialize environment variables.

If a credential has ever been pasted into a public issue, committed file, terminal transcript shared with others, or other untrusted surface, rotate it at the provider.

## Setup

The first runnable Python setup will land with the experiment harness. No credentials are required for unit tests.

## License

Private exploration. Not for distribution.
