# Framework integration contracts

**Documented / Source-inspected:** current official integrations converge on the same lifecycle:
derive a stable identity, retrieve profile/context before a turn, persist the completed exchange
afterward, and expose explicit recall/save tools where the framework supports tools. The exact
hook names differ; the tenancy and safety invariants do not.

**Observed (local):**
[`run_framework_integration_contract_matrix.py`](../experiments/run_framework_integration_contract_matrix.py)
executes that lifecycle across ten surfaces and fails the run if any context is unbounded, any
retrieval/capture crosses the exact container, any boundary is left open, or an ungranted MCP
write succeeds.

| Surface | Retrieval hook | Persistence hook | Practical wiring |
|---|---|---|---|
| Vercel AI SDK | model middleware | response capture | `withSupermemory`, full mode, stable `containerTag` and `customId` |
| OpenAI Agents | agent instructions/tool | post-run capture | inject bounded profile; expose explicit recall/save tools |
| LangChain | pre-invoke runnable | post-invoke runnable | wrap the chain boundary, not individual prompts |
| LangGraph | recall node | persist node | make memory edges explicit in graph state |
| Mastra | input processor | output processor | `withSupermemory`, fail closed on memory errors |
| Agno | pre-run context | post-run capture | keep identity derivation outside the agent |
| CrewAI | pre-kickoff context | post-kickoff capture | scope shared crew context to the authorized tenant |
| Convex | read action | write mutation | keep network reads in actions and durable app state in mutations |
| MCP | `recall` tool/resource | authorized `memory` tool | strict schemas; consume an external one-time grant for writes |
| Coding plugin | session-start hook | session-end hook | separate user, project, and custom scopes; review auto-capture |

## Reusable bridge

The bridge deliberately does not depend on any framework package. A thin adapter supplies the
framework's messages and receives a rendered, bounded `<retrieved-memory>` block:

```python
from pathlib import Path

from supermemory_lab.authorization import SqliteAuthorizationLedger
from supermemory_lab.framework_integrations import MemoryIntegrationBridge

ledger = SqliteAuthorizationLedger(
    Path("/secure/application/authorizations.sqlite3"),
    integrity_key=load_key_from_secret_manager(),
)
bridge = MemoryIntegrationBridge(
    memory_client,
    container_tag=authenticated_tenant_container,
    custom_id=application_conversation_id,
    authorization_ledger=ledger,
)

system_context = bridge.before_turn("langgraph", user_query)
bridge.after_turn(
    "langgraph",
    [
        {"role": "user", "content": user_query},
        {"role": "assistant", "content": final_answer},
    ],
)
```

For an explicit MCP/plugin save, a trusted application first grants the bridge's exact resource
hash, then the tool consumes it once:

```python
content = "User explicitly selected weekly concise updates."
resource_hash = bridge.memory_write_resource(content)
ledger.grant(
    scope="integration.memory.create",
    actor=authenticated_actor,
    resource_hash=resource_hash,
)
bridge.invoke_memory_tool(content, actor=authenticated_actor)
```

Use `TestingAuthorizationLedger` only in unit tests and synthetic harnesses. A production grant
must come from authenticated policy/UI state and live in a transactional service outside both
the model and Supermemory.

## Run it

```bash
PYTHONPATH=src python3 -m unittest tests.test_framework_integrations
PYTHONPATH=src python3 experiments/run_framework_integration_contract_matrix.py
```

The matrix covers configuration and the memory boundary; it does not claim that every third-party
runtime version was installed and exercised. Pin each adopted framework, add its real middleware
to CI, and replay these invariants before upgrading. Voice/no-code integrations remain outside
this ten-surface contract and should receive their own transport/authentication tests.

