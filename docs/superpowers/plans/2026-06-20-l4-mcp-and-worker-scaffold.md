# L4 — MCP Server + ARQ Worker Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Horizontal execution — Lane L4.** Runs concurrently with L1/L2/L3. **Branch:** `plan-5-mcp`. Merges 4th (last); rebase on post-Plan-2 `main` first. **Files are in NEW top-level dirs (`mcp_server/`, `worker/`) that no other lane touches** — the MCP server reaches the backend over HTTP (it does NOT import `app.models`), so Plan 2's model changes cannot break it. See `2026-06-20-horizontal-execution-map.md`.

**Goal:** Ship a standalone FastMCP (stdio) server that lets an MCP host (Claude Code) add and inspect Polingo words via the backend's HTTP API (Plan 5, ADR-0002), and scaffold an ARQ+Redis background worker for durable form generation (Plan 3 groundwork, ADR-0003) **without yet wiring it into the backend** (that integration touches L1-owned `words.py` and is deferred until Plan 2 merges).

**Architecture:** Two isolated new packages. `mcp_server/` is a FastMCP process speaking stdio to the host and HTTP to `http://localhost:8000/api`; it maps backend errors to structured text (stdio loses HTTP status codes). `worker/` defines an ARQ task that calls the existing LLM form-gen functions over HTTP-or-import seam, a `forms_status` state machine (`pending`/`ready`/`failed`), and an explicit retry/stuck policy — but ships as a runnable, tested scaffold with the backend wiring stubbed behind a clearly-marked integration point.

**Tech Stack:** Python 3.11+, FastMCP (`mcp`), `httpx`, ARQ, Redis, pytest, `respx`/`httpx.MockTransport` for HTTP mocking.

**Depends on:** Backend HTTP API (Plan 1, merged) — only the HTTP contract, frozen by L3. No source dependency on `backend-app/app`.

**Owned files:** `mcp_server/**`, `worker/**` only. Do NOT modify any `backend-app/` file (the worker→backend wiring is a later plan).

---

## Decisions to lock (open in ADR-0002/0003 — pinned here)

- **MCP transport:** stdio. **Backend base URL:** `MCP_BACKEND_URL` env, default `http://localhost:8000/api`.
- **Backend-unreachable behavior:** every MCP tool wraps HTTP calls; on connect error/timeout it returns a structured text payload `{"ok": false, "error": "...", "hint": "is the backend running on <url>?"}` rather than raising — so Claude sees *why*. Connect timeout 5s, 1 retry.
- **MCP tools (v1):** `add_word(text)`, `add_words_bulk(text)`, `check_word(text)`, `list_session_words()`, `get_stats()`. (Curation/management beyond add is deferred.)
- **forms_status state machine:** `pending → ready` on success; `pending → failed` after max retries. **Retry policy:** max 3 attempts, exponential backoff (base 5s). **Stuck:** a job `pending` with no active ARQ job > 10 min is re-enqueued by a periodic sweep (scaffolded, not scheduled in this plan). These constants live in `worker/config.py`.

---

### Task 1: MCP server package + HTTP backend client (TDD)

**Files:**
- Create: `mcp_server/__init__.py`, `mcp_server/requirements.txt`, `mcp_server/config.py`
- Create: `mcp_server/backend.py` (httpx client)
- Create: `mcp_server/tests/__init__.py`, `mcp_server/tests/test_backend.py`

- [ ] **Step 1: Create package + requirements + config**

Create `mcp_server/__init__.py` (empty).

Create `mcp_server/requirements.txt`:

```
mcp>=1.2
httpx>=0.27
pytest>=8.0
pytest-asyncio>=0.23
```

Create `mcp_server/config.py`:

```python
import os


def backend_url() -> str:
    """Base URL of the Polingo HTTP API (read at call time for test overrides)."""
    return os.getenv("MCP_BACKEND_URL", "http://localhost:8000/api")


CONNECT_TIMEOUT_S = 5.0
MAX_RETRIES = 1
```

- [ ] **Step 2: Write the failing backend-client test**

Create `mcp_server/tests/__init__.py` (empty), then `mcp_server/tests/test_backend.py`:

```python
import httpx
import pytest

from mcp_server.backend import BackendClient


@pytest.mark.asyncio
async def test_check_word_returns_parsed_json():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/words/check"
        return httpx.Response(200, json={"found": True, "word": {"id": 1}, "created": False})

    transport = httpx.MockTransport(handler)
    client = BackendClient(base_url="http://test/api", transport=transport)
    result = await client.check_word("kot")
    assert result["ok"] is True
    assert result["data"]["found"] is True


@pytest.mark.asyncio
async def test_unreachable_backend_returns_structured_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    transport = httpx.MockTransport(handler)
    client = BackendClient(base_url="http://test/api", transport=transport)
    result = await client.check_word("kot")
    assert result["ok"] is False
    assert "error" in result and "hint" in result
```

- [ ] **Step 3: Run it to confirm it fails**

Run: `cd mcp_server && python -m pytest tests/test_backend.py -v`
Expected: FAIL — `mcp_server.backend` does not exist.

> Install deps once: `python -m pip install -r mcp_server/requirements.txt` (use a venv; the backend `.venv` is fine).

- [ ] **Step 4: Implement the backend client**

Create `mcp_server/backend.py`:

```python
from typing import Any, Optional

import httpx

from mcp_server.config import CONNECT_TIMEOUT_S, MAX_RETRIES, backend_url


class BackendClient:
    """Thin async wrapper over the Polingo HTTP API. Never raises on transport
    failure — returns {"ok": bool, ...} so MCP tools can surface a reason."""

    def __init__(self, base_url: Optional[str] = None, transport=None):
        self._base_url = (base_url or backend_url()).rstrip("/")
        self._transport = transport

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(CONNECT_TIMEOUT_S),
            transport=self._transport,
        )

    async def _request(self, method: str, path: str, **kw) -> dict[str, Any]:
        last_exc = None
        for _ in range(MAX_RETRIES + 1):
            try:
                async with self._client() as c:
                    resp = await c.request(method, path, **kw)
                if resp.status_code >= 400:
                    return {"ok": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
                            "hint": f"backend at {self._base_url} rejected {method} {path}"}
                return {"ok": True, "data": resp.json()}
            except httpx.HTTPError as exc:
                last_exc = exc
        return {"ok": False, "error": str(last_exc),
                "hint": f"is the backend running at {self._base_url}?"}

    async def check_word(self, text: str) -> dict[str, Any]:
        return await self._request("POST", "/words/check", json={"text": text})

    async def add_words_bulk(self, text: str) -> dict[str, Any]:
        return await self._request("POST", "/words/check/bulk", json={"text": text})

    async def list_session_words(self) -> dict[str, Any]:
        return await self._request("GET", "/session/words/all")

    async def get_stats(self) -> dict[str, Any]:
        return await self._request("GET", "/stats")
```

> Note the base_url already ends in `/api`, so paths here are `/words/check` etc. The MockTransport test asserts `/api/words/check` because it sets base_url `http://test/api`.

- [ ] **Step 5: Run the test**

Run: `cd mcp_server && python -m pytest tests/test_backend.py -v`
Expected: PASS (2 passed).

- [ ] **Step 6: Commit**

```bash
git add mcp_server/__init__.py mcp_server/requirements.txt mcp_server/config.py mcp_server/backend.py mcp_server/tests
git commit -m "feat(mcp): backend HTTP client with structured-error passthrough"
```

---

### Task 2: MCP tools + stdio server

**Files:**
- Create: `mcp_server/server.py`
- Create: `mcp_server/tests/test_tools.py`
- Create: `mcp_server/README.md`

- [ ] **Step 1: Write the failing tool test**

The tools are thin async functions wrapping `BackendClient`; we test the formatting logic against a fake client.

Create `mcp_server/tests/test_tools.py`:

```python
import pytest

from mcp_server.server import add_word_tool, get_stats_tool


class _FakeBackend:
    def __init__(self, result):
        self._result = result

    async def check_word(self, text):
        return self._result

    async def get_stats(self):
        return self._result


@pytest.mark.asyncio
async def test_add_word_tool_success_message():
    backend = _FakeBackend({"ok": True, "data": {"found": True, "created": True,
                                                 "word": {"polish": "kot"}}})
    msg = await add_word_tool("kot", backend=backend)
    assert "kot" in msg
    assert "added" in msg.lower() or "created" in msg.lower()


@pytest.mark.asyncio
async def test_add_word_tool_surfaces_backend_down():
    backend = _FakeBackend({"ok": False, "error": "refused", "hint": "is the backend running?"})
    msg = await add_word_tool("kot", backend=backend)
    assert "refused" in msg or "running" in msg


@pytest.mark.asyncio
async def test_get_stats_tool_formats_numbers():
    backend = _FakeBackend({"ok": True, "data": {"today_percentage": 80.0, "trend": 5.0,
                                                 "overall_percentage": 75.0, "available_words": 42}})
    msg = await get_stats_tool(backend=backend)
    assert "42" in msg
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd mcp_server && python -m pytest tests/test_tools.py -v`
Expected: FAIL — `mcp_server.server` does not exist.

- [ ] **Step 3: Implement the tools + FastMCP wiring**

Create `mcp_server/server.py`. The `_tool` functions take an injectable `backend` for testing; the FastMCP-registered wrappers use a module default.

```python
from mcp.server.fastmcp import FastMCP

from mcp_server.backend import BackendClient

mcp = FastMCP("polingo")
_default_backend = BackendClient()


async def add_word_tool(text: str, backend=None) -> str:
    backend = backend or _default_backend
    r = await backend.check_word(text)
    if not r["ok"]:
        return f"Could not add '{text}': {r['error']} ({r['hint']})"
    d = r["data"]
    word = (d.get("word") or {}).get("polish", text)
    if d.get("created"):
        return f"Added new word '{word}'."
    if d.get("found"):
        return f"'{word}' already exists (matched {d.get('matched_field')})."
    return f"'{text}' could not be resolved."


async def add_words_bulk_tool(text: str, backend=None) -> str:
    backend = backend or _default_backend
    r = await backend.add_words_bulk(text)
    if not r["ok"]:
        return f"Bulk add failed: {r['error']} ({r['hint']})"
    d = r["data"]
    return (f"Added {d.get('added_count', 0)}, "
            f"{d.get('duplicate_count', 0)} duplicates, {d.get('failed_count', 0)} failed.")


async def list_session_words_tool(backend=None) -> str:
    backend = backend or _default_backend
    r = await backend.list_session_words()
    if not r["ok"]:
        return f"Could not list words: {r['error']} ({r['hint']})"
    words = r["data"].get("words", [])
    return f"{len(words)} words in session: " + ", ".join(w["polish"] for w in words[:50])


async def get_stats_tool(backend=None) -> str:
    backend = backend or _default_backend
    r = await backend.get_stats()
    if not r["ok"]:
        return f"Could not get stats: {r['error']} ({r['hint']})"
    d = r["data"]
    return (f"Today {d['today_percentage']}% (trend {d['trend']}), "
            f"overall {d['overall_percentage']}%, {d['available_words']} words available.")


# Register with FastMCP (thin wrappers so tests can call the *_tool fns directly)
@mcp.tool()
async def add_word(text: str) -> str:
    """Add a single Polish word (or phrase) to the learner's vocabulary."""
    return await add_word_tool(text)


@mcp.tool()
async def add_words_bulk(text: str) -> str:
    """Add multiple comma-separated words at once."""
    return await add_words_bulk_tool(text)


@mcp.tool()
async def list_session_words() -> str:
    """List the words currently in the learner's session."""
    return await list_session_words_tool()


@mcp.tool()
async def get_stats() -> str:
    """Get the learner's current practice statistics."""
    return await get_stats_tool()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tool tests**

Run: `cd mcp_server && python -m pytest tests/test_tools.py -v`
Expected: PASS.

- [ ] **Step 5: Smoke-check the server imports and registers tools**

Run: `cd mcp_server && python -c "from mcp_server.server import mcp; print('mcp ok')"`
Expected: prints `mcp ok` (no import error; FastMCP available).

- [ ] **Step 6: Write the README**

Create `mcp_server/README.md`:

```markdown
# Polingo MCP server (Plan 5)

Standalone FastMCP (stdio) server exposing word-management tools to an MCP host
(e.g. Claude Code). Calls the Polingo HTTP API; does NOT import backend models.

## Run
    python -m pip install -r requirements.txt
    MCP_BACKEND_URL=http://localhost:8000/api python -m mcp_server.server

## Tools
add_word · add_words_bulk · list_session_words · get_stats

## Errors
If the backend is unreachable, tools return a structured message explaining why
(stdio cannot carry HTTP status codes). Connect timeout 5s, 1 retry.

## Claude Code registration (example)
    claude mcp add polingo -- python -m mcp_server.server
```

- [ ] **Step 7: Commit**

```bash
git add mcp_server/server.py mcp_server/tests/test_tools.py mcp_server/README.md
git commit -m "feat(mcp): word-management tools over stdio (FastMCP)"
```

---

### Task 3: ARQ worker scaffold + forms_status state machine (TDD)

**Files:**
- Create: `worker/__init__.py`, `worker/requirements.txt`, `worker/config.py`
- Create: `worker/status.py` (pure state-machine helpers)
- Create: `worker/tasks.py` (ARQ task, backend wiring stubbed)
- Create: `worker/tests/__init__.py`, `worker/tests/test_status.py`, `worker/tests/test_tasks.py`
- Create: `worker/README.md`

This ships a runnable, tested scaffold. The actual call into form generation is behind a single injectable function so the L1 wiring (later plan) is a one-line swap.

- [ ] **Step 1: Create package, requirements, config**

Create `worker/__init__.py` (empty).

Create `worker/requirements.txt`:

```
arq>=0.26
redis>=5.0
httpx>=0.27
pytest>=8.0
pytest-asyncio>=0.23
```

Create `worker/config.py`:

```python
import os

MAX_ATTEMPTS = 3
BACKOFF_BASE_S = 5
STUCK_AFTER_S = 600  # 10 min with no active job → re-enqueue


def redis_url() -> str:
    return os.getenv("POLINGO_REDIS_URL", "redis://localhost:6379")
```

- [ ] **Step 2: Write the failing state-machine test**

Create `worker/tests/__init__.py` (empty), then `worker/tests/test_status.py`:

```python
from worker.status import FormsStatus, next_status_on_success, next_status_on_failure


def test_success_goes_ready():
    assert next_status_on_success() == FormsStatus.ready


def test_failure_under_max_stays_pending():
    assert next_status_on_failure(attempt=1) == FormsStatus.pending


def test_failure_at_max_goes_failed():
    assert next_status_on_failure(attempt=3) == FormsStatus.failed
```

- [ ] **Step 3: Run it to confirm it fails**

Run: `cd worker && python -m pytest tests/test_status.py -v`
Expected: FAIL — `worker.status` does not exist.

- [ ] **Step 4: Implement the state machine**

Create `worker/status.py`:

```python
from enum import Enum

from worker.config import MAX_ATTEMPTS


class FormsStatus(str, Enum):
    pending = "pending"
    ready = "ready"
    failed = "failed"


def next_status_on_success() -> FormsStatus:
    return FormsStatus.ready


def next_status_on_failure(attempt: int) -> FormsStatus:
    """attempt is 1-based. After MAX_ATTEMPTS, the word is terminally failed."""
    return FormsStatus.failed if attempt >= MAX_ATTEMPTS else FormsStatus.pending
```

- [ ] **Step 5: Run the state test**

Run: `cd worker && python -m pytest tests/test_status.py -v`
Expected: PASS.

- [ ] **Step 6: Write the failing task test**

Create `worker/tests/test_tasks.py`. The task calls an injectable `generate_fn` and reports the resulting status; the backend persistence is stubbed.

```python
import pytest

from worker.status import FormsStatus
from worker.tasks import generate_forms


@pytest.mark.asyncio
async def test_generate_forms_marks_ready_on_success():
    calls = {}

    async def fake_generate(word_id):
        calls["id"] = word_id
        return {"declensions": 7}

    async def fake_set_status(word_id, status):
        calls["status"] = status

    result = await generate_forms(
        {}, word_id=99, generate_fn=fake_generate, set_status_fn=fake_set_status
    )
    assert calls["id"] == 99
    assert calls["status"] == FormsStatus.ready
    assert result["status"] == FormsStatus.ready.value


@pytest.mark.asyncio
async def test_generate_forms_marks_failed_on_final_attempt():
    statuses = []

    async def boom(word_id):
        raise RuntimeError("llm down")

    async def fake_set_status(word_id, status):
        statuses.append(status)

    with pytest.raises(RuntimeError):
        await generate_forms(
            {"job_try": 3}, word_id=99, generate_fn=boom, set_status_fn=fake_set_status
        )
    assert statuses[-1] == FormsStatus.failed
```

- [ ] **Step 7: Run it to confirm it fails**

Run: `cd worker && python -m pytest tests/test_tasks.py -v`
Expected: FAIL — `worker.tasks` does not exist.

- [ ] **Step 8: Implement the task scaffold**

Create `worker/tasks.py`:

```python
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


class WorkerSettings:
    """ARQ entrypoint. `arq worker.tasks.WorkerSettings` runs this."""
    functions = [generate_forms]
    max_tries = MAX_ATTEMPTS

    @staticmethod
    def redis_settings():
        from arq.connections import RedisSettings
        return RedisSettings.from_dsn(redis_url())

    # Backoff: ARQ retries with its own delay; BACKOFF_BASE_S documents intent.
    retry_delay = BACKOFF_BASE_S
```

- [ ] **Step 9: Run the task tests**

Run: `cd worker && python -m pytest tests/test_tasks.py -v`
Expected: PASS.

- [ ] **Step 10: Write the README documenting the integration point**

Create `worker/README.md`:

```markdown
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
```

- [ ] **Step 11: Run the whole L4 suite**

Run: `cd mcp_server && python -m pytest tests/ -v && cd ../worker && python -m pytest tests/ -v`
Expected: all PASS.

- [ ] **Step 12: Commit**

```bash
git add worker
git commit -m "feat(worker): ARQ form-gen scaffold + forms_status state machine (Plan 3 groundwork)"
```

---

## Self-review

- MCP server: HTTP client with structured-error passthrough (Task 1) + 4 tools over stdio (Task 2) — covers ADR-0002's open decisions (timeout, retry, error passthrough). ✓
- Worker: forms_status machine + ARQ task scaffold with explicit retry/stuck constants (Task 3) — covers ADR-0003's open retry/dead-letter/stuck policy. ✓
- Full isolation: only `mcp_server/**` and `worker/**` created; no `backend-app/` edit; MCP reaches backend over HTTP, not by import — so Plan 2 cannot break this lane. ✓
- Worker→backend wiring explicitly deferred with a documented, injectable integration point (Task 3 Step 10) — honors the file-ownership manifest. ✓
- No placeholders: every function body, test, and command is concrete. The two `_not_wired`/`_noop` stubs are intentional, marked, and tested via injection. ✓
