from typing import Any, Awaitable, Callable, Optional

from worker.config import BACKOFF_BASE_S, MAX_ATTEMPTS, redis_url
from worker.status import FormsStatus, next_status_on_failure, next_status_on_success


async def _not_wired(word_id: int):  # pragma: no cover - replaced at integration
    raise NotImplementedError(
        "Form generation is not wired to the backend yet. Plan 3 integration "
        "injects the real generate_fn (calls app form-gen) when Plan 2 has merged."
    )


async def _set_status_noop(word_id: int, status: FormsStatus):  # pragma: no cover
    # Integration point: persist forms_status on the Word row (later plan).
    return None


async def generate_forms(
    ctx: dict,
    word_id: int,
    generate_fn: Optional[Callable[[int], Awaitable[Any]]] = None,
    set_status_fn: Optional[Callable[[int, FormsStatus], Awaitable[None]]] = None,
) -> dict:
    """ARQ task: generate forms for a word, driving the forms_status machine.

    ctx is ARQ's job context (carries job_try). generate_fn/set_status_fn are
    injectable for tests and for the deferred backend wiring."""
    generate_fn = generate_fn or _not_wired
    set_status_fn = set_status_fn or _set_status_noop
    attempt = int(ctx.get("job_try", 1))
    try:
        await generate_fn(word_id)
    except Exception:
        status = next_status_on_failure(attempt=attempt)
        await set_status_fn(word_id, status)
        raise  # let ARQ handle retry/backoff
    status = next_status_on_success()
    await set_status_fn(word_id, status)
    return {"word_id": word_id, "status": status.value}


from arq import func
from arq.connections import RedisSettings


class WorkerSettings:
    """ARQ entrypoint. `arq worker.tasks.WorkerSettings` runs this.

    NOTE (corrected per ARQ API): `redis_settings` is a plain ATTRIBUTE holding a
    RedisSettings instance — ARQ does NOT call it. `max_tries` is NOT a
    WorkerSettings field; it is set per-function via `func(...)`. There is no
    `retry_delay` on WorkerSettings — backoff is done by raising
    `arq.worker.Retry(defer=...)` inside the task (wired in the integration plan)."""
    functions = [func(generate_forms, name="generate_forms", max_tries=MAX_ATTEMPTS)]
    redis_settings = RedisSettings.from_dsn(redis_url())
