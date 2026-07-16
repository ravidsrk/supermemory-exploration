# Experiments

Experiments are opt-in and use isolated container tags prefixed with `lab:`. Raw run output goes to ignored `.runs/`; only manually reviewed, secret-free summaries belong in `evidence/`.

```bash
PYTHONPATH=src python3 -m supermemory_lab.probes
PYTHONPATH=src python3 -m supermemory_lab.probes --with-llm
```

The core probe exercises:

- v4 direct memory creation, search, profile, versioned update, and forgetting
- strict container isolation
- the undocumented/default search-mode question
- v3 document ingestion, processing, search, `customId` upsert, listing, and deletion
- v4 structured conversation ingestion
- optional profile-aware agent generation through OpenRouter

Do not paste raw run files into bug reports without reviewing them first. They contain synthetic experiment content and hosted resource IDs, but the redactor intentionally errs on the side of preserving useful response evidence.
