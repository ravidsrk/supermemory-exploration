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

The field lab includes hosted/self-hosted capability probes, nine authenticated provider
adapters, fifteen reference patterns, 52 offline tests, and live memory/no-memory experiments.
Start with the
[practical wiki](docs/README.md), [multi-provider agents](docs/practical-agents.md), or the
[verdict](docs/verdict.md).

## Repository map

| Path | Purpose |
|---|---|
| `docs/` | Durable practical wiki and research synthesis |
| `src/` | Reusable Supermemory client and agent patterns |
| `experiments/` | Reproducible live probes and evaluations |
| `tests/` | Offline contract and architecture tests |
| `evidence/` | Curated, secret-free observations from live runs |
| `examples/` | Runnable live agent patterns |

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

Python 3.9+ is sufficient; the field lab deliberately has no third-party Python dependency.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
cp .env.example .env.local
python -m unittest -v
```

Run the redacted capability probe, foundational patterns, or advanced agents:

```bash
supermemory-probe --with-llm
PYTHONPATH=src python examples/run_agent_patterns.py --pattern all
PYTHONPATH=src:. python experiments/run_advanced_agents.py debug
PYTHONPATH=src:. python experiments/run_advanced_agents.py continuity
PYTHONPATH=src python3 experiments/run_governance_scorecard.py
PYTHONPATH=src python3 experiments/run_signal_radar.py
PYTHONPATH=src python3 experiments/run_retrieval_policy_grid.py
```

Live commands create synthetic, isolated `lab:` containers. Raw probe output is ignored under
`.runs/`; the agent demo deliberately leaves its containers available for dashboard inspection.

## License

[MIT](LICENSE) © 2026 Ravindra Kumar.
