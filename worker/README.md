# Polingo form-gen worker scaffold (Plan 3 groundwork)

ARQ + Redis durable replacement for the current daemon-thread form generation
(`backend-app/app/api/words.py:266,359,480`). **Scaffold only** — not yet wired
to the backend, because that wiring edits L1-owned files and must wait until
Plan 2 merges.

## forms_status
pending → ready (success) · pending → failed (after MAX_ATTEMPTS=3).
Backoff base 5s. Stuck = pending with no active job > 10 min (sweep TODO).

## Integration point (later plan)
`generate_forms()` takes `generate_fn` and `set_status_fn`. The integration plan:
1. adds a `forms_status` column to Word (Alembic migration, backend lane),
2. implements `generate_fn` calling the existing LLM form-gen,
3. implements `set_status_fn` persisting the status,
4. replaces the `threading.Thread(...)` calls in words.py with `enqueue_job("generate_forms", word_id)`,
5. adds redis + worker services to docker-compose.

## Run (once wired + Redis up)
    python -m pip install -r requirements.txt
    arq worker.tasks.WorkerSettings
