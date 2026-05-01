# Decision 0002: Agent Instruction Layout

## Decision
Keep root `AGENTS.md` short and use `docs/agent-guidance/` for deeper durable instructions.

## Rationale
Agents need a compact entry point that points to maintained sources of truth. Long monolithic instruction files are harder to keep current and make relevant task context harder to find.

## Consequences
- New durable guidance belongs under `docs/agent-guidance/`.
- Root `AGENTS.md` should change only when the repository map or common commands change.
- Documentation drift should be fixed as part of feature work.

