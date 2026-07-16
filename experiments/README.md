# Experiments

Experiments are opt-in and use isolated container tags prefixed with `lab:`. Raw run output goes to ignored `.runs/`; only manually reviewed, secret-free summaries belong in `evidence/`.

```bash
PYTHONPATH=src python3 -m supermemory_lab.probes
PYTHONPATH=src python3 -m supermemory_lab.probes --with-llm
PYTHONPATH=src python3 -m supermemory_lab.probes --connector-only
PYTHONPATH=src python3 -m supermemory_lab.probes --router-only
PYTHONPATH=src python3 -m supermemory_lab.probes --scoped-key-only
```

The core probe exercises:

- v4 direct memory creation, search, profile, versioned update, and forgetting
- strict container isolation
- the undocumented/default search-mode question
- v3 document ingestion, processing, search, `customId` upsert, listing, and deletion
- v4 structured conversation ingestion
- optional profile-aware agent generation through OpenRouter
- optional OpenRouter-backed Memory Router continuation and isolation checks
- optional scoped-key read/write isolation, revocation, and cleanup checks

Do not paste raw run files into bug reports without reviewing them first. They contain synthetic experiment content and hosted resource IDs, but the redactor intentionally errs on the side of preserving useful response evidence.
