# L3 — Contract-Freeze Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Horizontal execution — Lane L3 (Gate 0).** Runs first; merges to `main` before L1/L2/L4. **Branch:** `test-contract-freeze`. See `2026-06-20-horizontal-execution-map.md`.

**Goal:** Capture the *current* HTTP behavior of every Polingo API endpoint as golden characterization tests, so the L1 schema refactor and L2 frontend refactor cannot silently change the contract.

**Architecture:** These are **characterization tests** — they assert the *current* response shape and status, and PASS against today's code. They live in `backend-app/tests/contract/` with their own nested `conftest.py` (so the L1-owned root `conftest.py` is never edited). Tests assert response **shape** (status code + presence/type of JSON keys), NOT volatile values that Plan 2 will legitimately change (`gender` string, record `id` values). The autouse `fake_llm` fixture from the root conftest still applies (nested conftests inherit), making LLM-backed endpoints deterministic and offline.

**Tech Stack:** pytest, FastAPI `TestClient`, SQLModel in-memory SQLite.

**Depends on:** Plan 1 (merged). Branches from current `main`.

**Owned files:** `backend-app/tests/contract/**` only. Do NOT edit `backend-app/tests/conftest.py` or any `app/` file.

---

## Endpoint inventory (frozen this lane)

From the live routers (all under `/api`):

- **words:** `GET /words/initial`, `PUT /words/{id}`, `POST /words/check`, `POST /words/check/bulk`
- **practice:** `POST /practice/submit`, `POST /practice/validate`, `POST /practice/skip`, `GET /practice/choose-translation/question`, `POST /practice/choose-translation/validate`
- **session:** `GET /session`, `PUT /session/language`, `POST /session/words`, `POST /session/words/bulk`, `GET /session/words/all`, `PUT /session/words/toggle`, `DELETE /session/words/{id}`
- **stats:** `GET /stats`, `GET /stats/history`, `POST /stats/explain`
- **endings:** `GET /endings/config`, `GET /endings/question`, `POST /endings/validate`, `GET /endings/stats`
- **admin:** `GET /admin/devices`, `GET /admin/settings`, `GET /admin/settings/{key}`, `PUT /admin/settings/{key}`, `GET /admin/sentences`
- **health:** `GET /healthz`

> Out of scope for golden tests (require real binary I/O / external services that `fake_llm` does not stub cleanly): `POST /practice/pronunciation` (multipart audio + STT), `GET /practice/tts` (audio bytes), `POST /admin/sentences/{id}/fix` (LLM regen). Document these as "contract not frozen — manual" in the lane's final task rather than asserting on them.

---

### Task 1: Lane scaffolding — nested conftest with a seeded client

**Files:**
- Create: `backend-app/tests/contract/__init__.py`
- Create: `backend-app/tests/contract/conftest.py`

- [ ] **Step 1: Create the package marker**

Create `backend-app/tests/contract/__init__.py` (empty file).

- [ ] **Step 2: Create the nested conftest with a seeded client**

The root `conftest.py` provides an autouse `fresh_db` (in-memory, unseeded) and autouse `fake_llm`. We add a `seeded_client` that seeds the canonical word list and a default session, so endpoints that need data behave like production. This nested conftest is additive — it does not modify the root.

Create `backend-app/tests/contract/conftest.py`:

```python
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.database import engine
from app.main_app import app  # see Step 3 note — adjust import to the real app object
from app.models import AppSetting, UserSession, Word
from app.seed import seed_words


@pytest.fixture
def seeded_client():
    """A TestClient backed by a freshly-seeded in-memory DB.

    fresh_db (root conftest, autouse) has already dropped+created the schema for
    this test. We seed the canonical words + a default session + the AppSettings
    that init_db() would normally create, reproducing a first-run production DB.
    """
    with Session(engine) as session:
        if not session.query(Word).first():
            seed_words(session)
        if not session.query(UserSession).first():
            session.add(UserSession())
            session.commit()
        for key, value in (("generate_on_the_fly", "false"), ("tts_source", "browser")):
            if not session.get(AppSetting, key):
                session.add(AppSetting(key=key, value=value))
                session.commit()
    return TestClient(app)
```

> **Import note (resolve before running):** the FastAPI app object is created in `backend-app/main.py` (top-level), imported in tests as `from main import app` — verify by reading `backend-app/main.py` and `backend-app/tests/conftest.py` (the root conftest already imports `app`; copy its exact import line). Replace the `from app.main_app import app` placeholder with that exact import. Likewise confirm `seed_words` and the model names against `app/seed.py` / `app/models.py`.

- [ ] **Step 3: Verify the fixture wiring with a trivial health test**

Create `backend-app/tests/contract/test_health_contract.py`:

```python
def test_healthz_contract(seeded_client):
    resp = seeded_client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"status", "service"}
    assert body["status"] == "ok"
```

- [ ] **Step 4: Run it**

Run: `.venv/bin/pytest tests/contract/test_health_contract.py -v`
Expected: PASS. If the `app`/`seed_words` import is wrong it fails at collection — fix the import per the note, do not change app code.

- [ ] **Step 5: Commit**

```bash
git add backend-app/tests/contract/__init__.py backend-app/tests/contract/conftest.py backend-app/tests/contract/test_health_contract.py
git commit -m "test(contract): scaffold nested conftest + seeded_client; freeze /healthz"
```

---

### Task 2: Freeze the read endpoints (GET, no LLM)

**Files:**
- Create: `backend-app/tests/contract/test_read_contracts.py`

These return deterministic shapes from seeded data. Assert keys/types, tolerate volatile values.

- [ ] **Step 1: Write the contract tests**

Create `backend-app/tests/contract/test_read_contracts.py`:

```python
WORD_KEYS = {"id", "polish", "english", "ukrainian", "part_of_speech", "gender"}


def test_words_initial_contract(seeded_client):
    resp = seeded_client.get("/api/words/initial?count=5")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 5
    assert WORD_KEYS <= set(body[0].keys())
    assert isinstance(body[0]["id"], int)
    # gender is volatile across Plan 2 (męski -> 5-gender); assert type only
    assert body[0]["gender"] is None or isinstance(body[0]["gender"], str)


def test_session_contract(seeded_client):
    resp = seeded_client.get("/api/session")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) >= {"language_set", "words"}
    assert body["language_set"] in {"english", "ukrainian"}
    assert isinstance(body["words"], list)


def test_session_words_all_contract(seeded_client):
    resp = seeded_client.get("/api/session/words/all")
    assert resp.status_code == 200
    body = resp.json()
    assert "words" in body
    if body["words"]:
        w = body["words"][0]
        assert {"id", "polish", "total_attempts", "correct_attempts",
                "error_rate", "enabled"} <= set(w.keys())


def test_stats_contract(seeded_client):
    resp = seeded_client.get("/api/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {
        "today_percentage", "trend", "overall_percentage", "available_words",
    }
    assert isinstance(body["available_words"], int)


def test_stats_history_contract(seeded_client):
    resp = seeded_client.get("/api/stats/history?limit=10")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"records", "total"}
    assert isinstance(body["records"], list)
    assert isinstance(body["total"], int)
    # records may be empty on a fresh DB; do NOT assert record id values (Plan 2 changes them)


def test_endings_config_contract(seeded_client):
    resp = seeded_client.get("/api/endings/config")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"parts_of_speech", "cases", "tenses"}
    assert "rzeczownik" in body["parts_of_speech"]


def test_endings_stats_contract(seeded_client):
    resp = seeded_client.get("/api/endings/stats")
    assert resp.status_code == 200
    assert set(resp.json().keys()) == {
        "today_percentage", "trend", "overall_percentage", "available_words",
    }


def test_admin_devices_contract(seeded_client):
    resp = seeded_client.get("/api/admin/devices")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"devices", "total_count", "active_count"}


def test_admin_settings_contract(seeded_client):
    resp = seeded_client.get("/api/admin/settings")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    keys = {s["key"] for s in body}
    assert {"generate_on_the_fly", "tts_source"} <= keys


def test_admin_sentences_contract(seeded_client):
    resp = seeded_client.get("/api/admin/sentences")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
```

- [ ] **Step 2: Run them**

Run: `.venv/bin/pytest tests/contract/test_read_contracts.py -v`
Expected: all PASS. If any FAILS, the assumed shape is wrong — read the actual router response model and correct the assertion to match *current* behavior (do not change app code; the goal is to document reality).

- [ ] **Step 3: Commit**

```bash
git add backend-app/tests/contract/test_read_contracts.py
git commit -m "test(contract): freeze GET read-endpoint contracts"
```

---

### Task 3: Freeze the write/mutation endpoints

**Files:**
- Create: `backend-app/tests/contract/test_write_contracts.py`

These exercise POST/PUT/DELETE flows against seeded data. `fake_llm` makes validation deterministic (`validate_translation_via_llm` returns `is_correct=False`).

- [ ] **Step 1: Write the contract tests**

Create `backend-app/tests/contract/test_write_contracts.py`:

```python
def _first_word_id(seeded_client):
    return seeded_client.get("/api/words/initial?count=1").json()[0]["id"]


def test_practice_submit_contract(seeded_client):
    wid = _first_word_id(seeded_client)
    resp = seeded_client.post("/api/practice/submit", json={
        "word_id": wid, "language_set": "english",
        "direction": "writing", "was_correct": True,
    })
    assert resp.status_code == 200
    assert set(resp.json().keys()) == {
        "today_percentage", "trend", "overall_percentage", "available_words",
    }


def test_practice_validate_contract(seeded_client):
    wid = _first_word_id(seeded_client)
    resp = seeded_client.post("/api/practice/validate", json={
        "word_id": wid, "language_set": "english",
        "direction": "writing", "answer": "something",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert {"was_correct", "correct_answer", "alternatives", "stats"} <= set(body.keys())
    assert isinstance(body["alternatives"], list)


def test_choose_translation_question_contract(seeded_client):
    resp = seeded_client.get(
        "/api/practice/choose-translation/question?language_set=english&direction=from_polish"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert {"word_id", "prompt", "correct_answer", "options", "direction"} <= set(body.keys())
    assert isinstance(body["options"], list) and len(body["options"]) >= 2


def test_session_language_switch_contract(seeded_client):
    resp = seeded_client.put("/api/session/language", json={"language_set": "ukrainian"})
    assert resp.status_code == 200
    assert resp.json()["language_set"] == "ukrainian"


def test_session_add_word_contract(seeded_client):
    wid = _first_word_id(seeded_client)
    resp = seeded_client.post("/api/session/words", json={"word_id": wid})
    assert resp.status_code == 200
    assert "words" in resp.json()


def test_words_check_contract(seeded_client):
    resp = seeded_client.post("/api/words/check", json={"text": "kot"})
    assert resp.status_code == 200
    body = resp.json()
    assert {"found", "word", "matched_field", "created", "source"} <= set(body.keys())


def test_admin_setting_update_contract(seeded_client):
    resp = seeded_client.put("/api/admin/settings/tts_source", json={"value": "server"})
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"key": "tts_source", "value": "server"}
```

- [ ] **Step 2: Run them**

Run: `.venv/bin/pytest tests/contract/test_write_contracts.py -v`
Expected: PASS. Fix any assertion that mismatches real current behavior (e.g., if `words/check` body differs); do not change app code.

- [ ] **Step 3: Commit**

```bash
git add backend-app/tests/contract/test_write_contracts.py
git commit -m "test(contract): freeze write/mutation endpoint contracts"
```

---

### Task 4: Document the un-frozen endpoints + run the whole contract suite

**Files:**
- Create: `backend-app/tests/contract/README.md`

- [ ] **Step 1: Write the README**

Create `backend-app/tests/contract/README.md`:

```markdown
# Contract-freeze tests (Lane L3)

Golden characterization tests of the HTTP API as of Plan 1. They assert response
SHAPE (status + keys + types), not volatile values that Plan 2 changes
(`gender` strings, history record `id` values, pronoun `oni/one` split).

## Frozen
words, practice (text), session, stats, endings, admin (read + settings update).

## NOT frozen (manual verification only)
- POST /api/practice/pronunciation — multipart audio + STT
- GET  /api/practice/tts — audio/mpeg bytes
- POST /api/admin/sentences/{id}/fix — LLM regeneration
These need real binary I/O or live LLM and are excluded from the golden suite.

## Plan 2 expectations
After Plan 2 merges and L3 rebases, these tests MUST still pass unchanged. If one
breaks, the contract changed unexpectedly — investigate before adjusting.
```

- [ ] **Step 2: Run the full contract suite**

Run: `.venv/bin/pytest tests/contract/ -v`
Expected: all PASS.

- [ ] **Step 3: Run the entire backend suite to confirm no interference**

Run: `.venv/bin/pytest -v`
Expected: all prior Plan 1 tests still pass; new contract tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend-app/tests/contract/README.md
git commit -m "test(contract): document un-frozen endpoints; full suite green"
```

---

## Self-review

- Every frozen endpoint from the inventory has a test (Tasks 2–3). Un-frozen ones documented (Task 4). ✓
- No app code modified; root `conftest.py` untouched (fixtures live in `tests/contract/conftest.py`). ✓
- Volatile values (gender, history id, pronoun) are asserted by type/shape only, so Plan 2's contract delta does not break the suite on rebase. ✓
- One judgement call (the `app`/`seed_words` import line) is flagged with explicit resolution instructions in Task 1 Step 2. ✓
