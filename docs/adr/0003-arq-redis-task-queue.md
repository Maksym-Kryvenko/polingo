---
Status: proposed
Date: 2026-06-17
---

# Form generation via ARQ + Redis task queue

> **Status note:** Target design. The repo currently generates forms in fire-and-forget `threading.Thread(daemon=True)` calls (`words.py:266,359,480`); there is no arq/redis dependency and no `forms_status` column.

LLM-driven generation of declensions/conjugations/practice-sentences will run as durable background jobs on **ARQ** (async Redis queue) with a dedicated worker, replacing the daemon threads. Each Word carries a `forms_status` (pending/ready/failed); practice only serves `ready` Words.

ARQ is async-native (matches FastAPI) and gives real retries, scheduling, and restart-survival, which the current daemon threads cannot (work is lost on restart and has no status).

## Considered options

- **Huey with a SQLite backend** — a real queue (retries, scheduling, persistence, dedicated worker) with **no new infrastructure**, matching the single-user SQLite footprint. Rejected only because we want async-native integration with FastAPI and headroom for concurrent bulk generation; this remains the natural fallback if Redis becomes unwanted.
- **Keep daemon threads** — rejected: no retries, no status, lost on restart.
- **Synchronous generation on add** — rejected: blocks add-word for seconds, bad for bulk/MCP.

## Consequences

- **Adds a Redis service to the Compose stack** for an otherwise single-user SQLite app — the most significant cost, and heavier than the Huey/SQLite alternative. Accepted deliberately for async integration + concurrency headroom (e.g. bulk adds from MCP).
- **Reversibility is real but not free.** The job interface is narrow enough to swap for Huey/SQLite later, but doing so means removing the Redis service and rewriting worker wiring — non-trivial, hence recording the decision here.
- **Retry/failure policy must be defined, not assumed.** "failed/stuck jobs are retried" needs concrete values: max retries, backoff, a terminal `failed` state (and how a Word in `failed` surfaces to UI/MCP), and what counts as "stuck." Decide where these constants live before the worker ships.
