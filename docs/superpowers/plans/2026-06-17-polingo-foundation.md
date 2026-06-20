# Polingo Foundation & Correctness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Polingo backend testable and config-driven, and fix three confirmed correctness defects (LLM answer-persist ratchet, SQLite lock timeout, wrong accusative-plural grammar), without changing the database schema.

**Architecture:** Introduce a tiny env-based config seam so the SQLAlchemy engine and all model ids stop being hard-coded; this same seam lets tests run against an in-memory SQLite database with faked LLM calls. Then apply targeted correctness fixes under TDD. No schema migration happens here — `Attempt` unification and the virility model (B1) are deferred to Plan 2, which introduces Alembic to do them safely.

**Tech Stack:** Python 3.11+, FastAPI, SQLModel/SQLAlchemy, SQLite, pytest, FastAPI `TestClient`, OpenAI SDK.

**Out of scope (later plans):** Alembic, unified `Attempt` table, virility/męskoosobowy schema axis (B1), ARQ+Redis, the Topic×Format exercise engine, MCP server, frontend split, promptfoo evals.

---

## File structure

| File | Responsibility | Status |
|---|---|---|
| `backend-app/app/config.py` | Single source of env-driven settings (DB URL, model ids, TTS voice). Functions, read at call-time, so tests can override via env. | Create |
| `backend-app/app/database.py` | Build engine from `config`; StaticPool for in-memory; `timeout=30` for file DBs; fail-loud migration. | Modify |
| `backend-app/app/llm.py` | Read model ids from `config` instead of the hard-coded `MODEL`/audio constants. | Modify |
| `backend-app/app/api/stats.py` | Stop importing the removed `MODEL` constant; use `config`. | Modify |
| `backend-app/app/api/practice.py` | Remove the auto-persist of LLM-approved answers into `WordOption` (M2). | Modify |
| `backend-app/app/grammar.py` | Correct masculine accusative-plural rule; label virile vs non-virile nominative-plural (B2/M10). | Modify |
| `backend-app/requirements.txt` | Add `pytest`. | Modify |
| `backend-app/pytest.ini` | Configure pytest (test paths, set in-memory DB env before import). | Create |
| `backend-app/tests/conftest.py` | Fixtures: fresh in-memory DB per test, `TestClient`, autouse fake-LLM. | Create |
| `backend-app/tests/test_config.py` | Tests for the config seam. | Create |
| `backend-app/tests/test_database.py` | Tests for engine selection + idempotent fail-loud migration. | Create |
| `backend-app/tests/test_practice_grading.py` | Tests for the M2 fix. | Create |
| `backend-app/tests/test_grammar_reference.py` | Tests for the B2/M10 grammar fix. | Create |

> All commands below assume the working directory is `backend-app/` unless stated. Run `python -m pip install -r requirements.txt` once after Task 1.

---

### Task 1: Add pytest and the config seam

**Files:**
- Modify: `backend-app/requirements.txt`
- Create: `backend-app/app/config.py`
- Create: `backend-app/tests/test_config.py`
- Create: `backend-app/pytest.ini`

- [ ] **Step 1: Add pytest to requirements**

Modify `backend-app/requirements.txt`, append one line:

```
pytest>=8.0
```

- [ ] **Step 2: Install**

Run: `python -m pip install -r requirements.txt`
Expected: pytest installs successfully.

- [ ] **Step 3: Create pytest config**

Create `backend-app/pytest.ini`. Setting the env var here guarantees it is set before any `app.*` module is imported by a test, so the engine is built against in-memory SQLite.

```ini
[pytest]
testpaths = tests
env =
addopts = -q
[pytest:env]
POLINGO_DATABASE_URL = sqlite://
```

> Note: `pytest.ini` does not natively read `[pytest:env]`. We instead set the env var at the top of `conftest.py` (Task 2). Keep this file minimal:

```ini
[pytest]
testpaths = tests
addopts = -q
```

- [ ] **Step 4: Write the failing test for config**

Create `backend-app/tests/test_config.py`:

```python
from app import config


def test_database_url_defaults_to_container_path(monkeypatch):
    monkeypatch.delenv("POLINGO_DATABASE_URL", raising=False)
    assert config.database_url() == "sqlite:////app/data/polingo.db"


def test_database_url_reads_env_at_call_time(monkeypatch):
    monkeypatch.setenv("POLINGO_DATABASE_URL", "sqlite:///./custom.db")
    assert config.database_url() == "sqlite:///./custom.db"


def test_text_model_default_and_override(monkeypatch):
    monkeypatch.delenv("POLINGO_TEXT_MODEL", raising=False)
    assert config.text_model() == "gpt-5-mini"
    monkeypatch.setenv("POLINGO_TEXT_MODEL", "gpt-test")
    assert config.text_model() == "gpt-test"


def test_audio_model_defaults(monkeypatch):
    monkeypatch.delenv("POLINGO_STT_MODEL", raising=False)
    monkeypatch.delenv("POLINGO_TTS_MODEL", raising=False)
    monkeypatch.delenv("POLINGO_TTS_VOICE", raising=False)
    assert config.stt_model() == "whisper-1"
    assert config.tts_model() == "tts-1"
    assert config.tts_voice() == "nova"
```

- [ ] **Step 5: Run it to confirm it fails**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.config'`.

- [ ] **Step 6: Implement config**

Create `backend-app/app/config.py`:

```python
"""Env-driven settings. Functions (not constants) so values are read at call
time — this lets tests override behaviour with monkeypatch.setenv."""

import os


def database_url() -> str:
    return os.getenv("POLINGO_DATABASE_URL", "sqlite:////app/data/polingo.db")


def text_model() -> str:
    return os.getenv("POLINGO_TEXT_MODEL", "gpt-5-mini")


def stt_model() -> str:
    return os.getenv("POLINGO_STT_MODEL", "whisper-1")


def tts_model() -> str:
    return os.getenv("POLINGO_TTS_MODEL", "tts-1")


def tts_voice() -> str:
    return os.getenv("POLINGO_TTS_VOICE", "nova")
```

- [ ] **Step 7: Run it to confirm it passes**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS (4 passed).

- [ ] **Step 8: Commit**

```bash
git add backend-app/requirements.txt backend-app/pytest.ini backend-app/app/config.py backend-app/tests/test_config.py
git commit -m "feat: add pytest and env-driven config seam"
```

---

### Task 2: Build the engine from config + test harness

**Files:**
- Modify: `backend-app/app/database.py:6-11`
- Create: `backend-app/tests/conftest.py`
- Create: `backend-app/tests/test_database.py`

- [ ] **Step 1: Write the failing test for engine selection**

Create `backend-app/tests/test_database.py`:

```python
from sqlalchemy.pool import StaticPool

from app import database


def test_in_memory_url_uses_static_pool():
    eng = database.make_engine("sqlite://")
    assert eng.pool.__class__ is StaticPool


def test_file_url_sets_busy_timeout():
    eng = database.make_engine("sqlite:///./tmp_timeout_test.db")
    # connect_args are stored on the engine's dialect creator kwargs
    assert eng.url.database == "./tmp_timeout_test.db"
    with eng.connect() as conn:
        # busy_timeout pragma is set to 30000ms (30s) via connect_args timeout=30
        result = conn.exec_driver_sql("PRAGMA busy_timeout").scalar()
    assert result == 30000


def test_migration_is_idempotent_on_memory():
    # Memory DBs are skipped by the migrator; calling twice must not raise.
    database.init_db()
    database.init_db()
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `python -m pytest tests/test_database.py -v`
Expected: FAIL — `AttributeError: module 'app.database' has no attribute 'make_engine'`.

- [ ] **Step 3: Refactor database.py**

Replace lines `backend-app/app/database.py:1-39` (the imports, `DATABASE_URL`, `engine`, and `_migrate_add_columns`) with:

```python
import logging
import sqlite3

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app import config
from app.models import AppSetting, UserSession, Word
from app.seed import seed_words

logger = logging.getLogger("polingo.database")

_MEMORY_URLS = {"sqlite://", "sqlite:///:memory:"}


def make_engine(url: str):
    """Create an engine. In-memory DBs need StaticPool so every connection
    shares one database; file DBs get a 30s busy timeout to avoid 'database
    is locked' under concurrent writes (M9)."""
    if url in _MEMORY_URLS:
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_engine(
        url,
        connect_args={"check_same_thread": False, "timeout": 30},
    )


engine = make_engine(config.database_url())


def _migrate_add_columns(engine) -> None:
    """Add new nullable columns to existing tables if missing. Swallows ONLY
    the 'duplicate column' case; every other failure is logged and re-raised
    so a broken migration cannot start the app silently (B3)."""
    db_path = engine.url.database
    if db_path in (None, ":memory:"):
        return  # in-memory DB: create_all already built the current schema
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        for table, column in [
            ("practicerecord", "user_answer"),
            ("practicerecord", "correct_answer"),
            ("endingspracticerecord", "user_answer"),
            ("endingspracticerecord", "correct_answer"),
        ]:
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT")
            except sqlite3.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    logger.error("Migration failed on %s.%s: %s", table, column, exc)
                    raise
        conn.commit()
    finally:
        conn.close()
```

> Leave the existing `init_db()` and `get_session()` definitions (lines 37-58) in place below this block — they already call `SQLModel.metadata.create_all(engine)` then `_migrate_add_columns(engine)`.

- [ ] **Step 4: Run it to confirm it passes**

Run: `python -m pytest tests/test_database.py -v`
Expected: PASS (3 passed). Delete the stray file afterward: `rm -f tmp_timeout_test.db`.

- [ ] **Step 5: Create the test harness (conftest)**

Create `backend-app/tests/conftest.py`:

```python
import os

# MUST run before any `app.*` import so the engine builds against memory.
os.environ.setdefault("POLINGO_DATABASE_URL", "sqlite://")
os.environ.setdefault("OPENAI_API_KEY", "test-key-not-used")

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from app.database import engine
from main import app


@pytest.fixture(autouse=True)
def fresh_db():
    """Empty schema per test (no seed) for full isolation."""
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def client():
    # No `with` block: we don't want the startup event to seed/re-init,
    # fresh_db owns schema lifecycle.
    return TestClient(app)


@pytest.fixture(autouse=True)
def fake_llm(monkeypatch):
    """Replace every network LLM call with a deterministic fake so tests are
    offline and fast. Individual tests can re-monkeypatch for specific cases."""
    from app import llm

    monkeypatch.setattr(llm, "resolve_word_via_llm", lambda text: {
        "detected_language": "polish", "corrected_input": text,
        "polish": text, "english": text, "ukrainian": text,
        "part_of_speech": "inne", "gender": None,
    })
    monkeypatch.setattr(llm, "validate_translation_via_llm", lambda **kw: {
        "is_correct": False, "normalized_answer": "", "rationale": "fake",
    })
    monkeypatch.setattr(llm, "generate_declensions_via_llm", lambda *a, **k: [])
    monkeypatch.setattr(llm, "generate_verb_conjugations_via_llm", lambda *a, **k: {})
    monkeypatch.setattr(llm, "generate_practice_sentences_via_llm", lambda *a, **k: [])
```

- [ ] **Step 6: Write a smoke test proving the harness works**

Append to `backend-app/tests/test_database.py`:

```python
def test_healthz_via_client(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "service": "polingo"}
```

- [ ] **Step 7: Run the full suite**

Run: `python -m pytest -v`
Expected: PASS — config + database + smoke tests all green.

- [ ] **Step 8: Commit**

```bash
git add backend-app/app/database.py backend-app/tests/conftest.py backend-app/tests/test_database.py
git commit -m "feat: build engine from config; add test harness; fail-loud migration (B3) and SQLite timeout (M9)"
```

---

### Task 3: Route model ids through config

**Files:**
- Modify: `backend-app/app/llm.py` (the `MODEL` constant + all `model=` call sites + audio models/voice)
- Modify: `backend-app/app/api/stats.py:5` (import of `MODEL`) and its `model=` usage

- [ ] **Step 1: Write the failing test**

Create `backend-app/tests/test_llm_config.py`:

```python
import inspect

from app import config, llm


def test_llm_has_no_hardcoded_model_constant():
    # MODEL must be gone; ids come from config now.
    assert not hasattr(llm, "MODEL")


def test_text_model_is_config_driven(monkeypatch):
    monkeypatch.setenv("POLINGO_TEXT_MODEL", "gpt-from-env")
    assert config.text_model() == "gpt-from-env"


def test_llm_source_references_config_text_model():
    src = inspect.getsource(llm)
    assert "config.text_model()" in src
    assert '"gpt-5-mini"' not in src  # no hard-coded id left in llm.py
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `python -m pytest tests/test_llm_config.py -v`
Expected: FAIL — `MODEL` still exists / `config.text_model()` not referenced.

- [ ] **Step 3: Edit llm.py**

In `backend-app/app/llm.py`:

1. Add the import near the top (after the existing `from app.models import ...`):

```python
from app import config
```

2. Delete the constant line `MODEL = "gpt-5-mini"` (currently `llm.py:22`).

3. Replace every occurrence of `model=MODEL` with `model=config.text_model()` (there are several: in `resolve_word_via_llm`, `validate_translation_via_llm`, `evaluate_pronunciation_via_llm`, `generate_verb_conjugations_via_llm`, `generate_declensions_via_llm`, `generate_practice_sentences_via_llm`, `generate_sentence_on_the_fly`, `fix_sentence_via_llm`). Use an editor replace-all on the literal `model=MODEL`.

4. In `transcribe_audio`, replace `model="whisper-1"` with `model=config.stt_model()`.

5. In `text_to_speech`, replace `model="tts-1"` with `model=config.tts_model()` and `voice="nova"` with `voice=config.tts_voice()`.

- [ ] **Step 4: Edit stats.py**

In `backend-app/app/api/stats.py`:

1. Change the import line `from app.llm import get_openai_client, MODEL` to:

```python
from app import config
from app.llm import get_openai_client
```

2. In `explain_answer`, change `model=MODEL` to `model=config.text_model()`.

- [ ] **Step 5: Run the tests**

Run: `python -m pytest tests/test_llm_config.py -v`
Expected: PASS (3 passed).

- [ ] **Step 6: Run the full suite to confirm nothing broke**

Run: `python -m pytest -v`
Expected: PASS (all green — the import of `stats.py` no longer references a missing `MODEL`).

- [ ] **Step 7: Commit**

```bash
git add backend-app/app/llm.py backend-app/app/api/stats.py backend-app/tests/test_llm_config.py
git commit -m "refactor: route LLM model ids through config (no hard-coded models)"
```

---

### Task 4: Fix the LLM answer-persist ratchet (M2)

**Background:** In `practice.py`, when the LLM judges a free-text answer "correct," the normalized answer is permanently inserted as a `WordOption` and thereafter matched directly — bypassing the LLM forever. For Polish a "slightly off" answer is frequently a *different case form*, so a single lenient LLM call can poison the accepted-answers set permanently. The fix: still accept the answer for this attempt, but **do not auto-persist it** as a canonical option.

**Files:**
- Modify: `backend-app/app/api/practice.py:98-117`
- Create: `backend-app/tests/test_practice_grading.py`

- [ ] **Step 1: Write the failing test**

Create `backend-app/tests/test_practice_grading.py`:

```python
from sqlmodel import Session, select

from app.database import engine
from app.models import Word, WordOption


def _make_word() -> int:
    with Session(engine) as s:
        w = Word(polish="kot", english="cat", ukrainian="кіт", part_of_speech="rzeczownik", gender="męski")
        s.add(w)
        s.commit()
        s.refresh(w)
        return w.id


def test_llm_correct_answer_is_not_persisted_as_option(client, monkeypatch):
    from app import llm
    # Force the LLM to "approve" a wrong-looking answer.
    monkeypatch.setattr(llm, "validate_translation_via_llm", lambda **kw: {
        "is_correct": True, "normalized_answer": "kota", "rationale": "fake-approve",
    })
    word_id = _make_word()

    resp = client.post("/api/practice/validate", json={
        "word_id": word_id,
        "language_set": "english",
        "direction": "writing",
        "answer": "kota",
    })
    assert resp.status_code == 200
    assert resp.json()["was_correct"] is True

    # The key assertion: nothing was written to WordOption.
    with Session(engine) as s:
        options = s.exec(select(WordOption).where(WordOption.word_id == word_id)).all()
    assert options == []
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `python -m pytest tests/test_practice_grading.py -v`
Expected: FAIL — a `WordOption` row with value `kota` is created, so `options != []`.

- [ ] **Step 3: Apply the fix**

In `backend-app/app/api/practice.py`, replace the block currently at lines 98-117:

```python
            if llm_validation.get("is_correct"):
                corrected = llm_validation.get("normalized_answer") or payload.answer
                is_correct = True
                matched_via = "llm"
                exists = session.exec(
                    select(WordOption).where(
                        WordOption.word_id == word.id,
                        WordOption.language == target_language,
                        WordOption.value == corrected,
                    )
                ).first()
                if not exists:
                    session.add(
                        WordOption(
                            word_id=word.id,
                            language=target_language,
                            value=corrected,
                        )
                    )
                    session.commit()
```

with:

```python
            if llm_validation.get("is_correct"):
                # Accept for THIS attempt only. Do not auto-persist as a
                # canonical WordOption: a lenient LLM call would otherwise
                # permanently whitelist a wrong (often miscased) form (M2).
                is_correct = True
                matched_via = "llm"
```

- [ ] **Step 4: Run the test to confirm it passes**

Run: `python -m pytest tests/test_practice_grading.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend-app/app/api/practice.py backend-app/tests/test_practice_grading.py
git commit -m "fix: stop auto-persisting LLM-approved answers as canonical options (M2)"
```

---

### Task 5: Correct the masculine accusative-plural grammar (B2 + M10)

**Background:** `grammar.py` writes the masculine **plural** biernik (accusative) as `żywotne: =dop., nieżywotne: =mian.` — that is the *singular* animacy rule wrongly applied to plural. The correct plural rule splits on **virility**: virile (męskoosobowy) → genitive plural (`widzę studentów`); non-virile → nominative plural (`widzę koty`, never `*kotów`). The same correction applies to the adjective table. We also label the nominative-plural masculine entries virile vs non-virile (M10) since `-i/-y` triggers a virile-only consonant alternation.

> This is a **pure reference-data fix** — no schema change. (The full virility *model* axis on `Word`/`Pronoun`, B1, is Plan 2.)

**Files:**
- Modify: `backend-app/app/grammar.py:7` (noun mianownik męski), `:22` (noun biernik męski), `:47` (adj mianownik męski), `:62` (adj biernik męski)
- Create: `backend-app/tests/test_grammar_reference.py`

- [ ] **Step 1: Write the failing test**

Create `backend-app/tests/test_grammar_reference.py`:

```python
from app.grammar import NOUN_ENDINGS, ADJECTIVE_ENDINGS, get_grammar_reference


def test_noun_accusative_masc_plural_uses_virility_not_animacy():
    plural = NOUN_ENDINGS["biernik"]["męski"]["plural"]
    # The wrong (singular) animacy wording must be gone...
    assert "żywotne" not in plural
    # ...and the correct virility split must be present.
    assert "męskoosobowy" in plural
    assert "niemęskoosobowy" in plural


def test_adjective_accusative_masc_plural_uses_virility():
    plural = ADJECTIVE_ENDINGS["biernik"]["męski"]["plural"]
    assert "żywotne" not in plural
    assert "męskoosobowy" in plural


def test_noun_nominative_masc_plural_labels_virility():
    plural = NOUN_ENDINGS["mianownik"]["męski"]["plural"]
    assert "męskoosobowy" in plural


def test_get_grammar_reference_still_returns_biernik_noun_notes():
    ref = get_grammar_reference("rzeczownik", case="biernik")
    assert "endings" in ref and "notes" in ref
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `python -m pytest tests/test_grammar_reference.py -v`
Expected: FAIL — current strings still contain `żywotne` and lack `męskoosobowy`.

- [ ] **Step 3: Fix the noun tables**

In `backend-app/app/grammar.py`, in `NOUN_ENDINGS`:

Replace the `mianownik` → `męski` line (currently `:7`):

```python
        "męski": {"singular": "-", "plural": "-i/-y/-owie/-e", "examples": "kot → koty, pan → panowie"},
```

with:

```python
        "męski": {"singular": "-", "plural": "męskoosobowy: -i/-y/-owie (z alternacją: student→studenci); niemęskoosobowy: -y/-e (kot→koty)", "examples": "studenci (m-os.), koty (niem-os.)"},
```

Replace the `biernik` → `męski` line (currently `:22`):

```python
        "męski": {"singular": "żywotne: =dop., nieżywotne: =mian.", "plural": "żywotne: =dop., nieżywotne: =mian.", "examples": "kota (żyw.), dom (nieżyw.)"},
```

with:

```python
        "męski": {"singular": "żywotne: =dopełniacz (widzę kota), nieżywotne: =mianownik (widzę dom)", "plural": "męskoosobowy: =dopełniacz l.mn. (widzę studentów), niemęskoosobowy: =mianownik l.mn. (widzę koty, domy)", "examples": "kota/dom (l.poj.); studentów/koty (l.mn.)"},
```

- [ ] **Step 4: Fix the adjective tables**

In `ADJECTIVE_ENDINGS`:

Replace the `mianownik` → `męski` line (currently `:47`):

```python
        "męski": {"singular": "-y/-i", "plural": "-e/-i/-y", "examples": "dobry, duży, dobrzy"},
```

with:

```python
        "męski": {"singular": "-y/-i", "plural": "męskoosobowy: -i/-y (z alternacją: dobry→dobrzy); niemęskoosobowy: -e (dobre)", "examples": "dobrzy (m-os.), dobre (niem-os.)"},
```

Replace the `biernik` → `męski` line (currently `:62`):

```python
        "męski": {"singular": "żywotne: =dop., nieżywotne: =mian.", "plural": "żywotne: =dop., nieżywotne: =mian.", "examples": "dobrego (żyw.), dobry (nieżyw.)"},
```

with:

```python
        "męski": {"singular": "żywotne: =dopełniacz (dobrego), nieżywotne: =mianownik (dobry)", "plural": "męskoosobowy: =dopełniacz l.mn. (dobrych), niemęskoosobowy: =mianownik l.mn. (dobre)", "examples": "dobrych (m-os.), dobre (niem-os.)"},
```

- [ ] **Step 5: Run the tests to confirm they pass**

Run: `python -m pytest tests/test_grammar_reference.py -v`
Expected: PASS (4 passed).

- [ ] **Step 6: Run the full suite**

Run: `python -m pytest -v`
Expected: PASS (all tasks green).

- [ ] **Step 7: Commit**

```bash
git add backend-app/app/grammar.py backend-app/tests/test_grammar_reference.py
git commit -m "fix: correct masculine accusative-plural rule to virility split (B2); label nominative-plural virility (M10)"
```

---

### Task 6: Update README and .env.example for the new config

**Files:**
- Modify: `backend-app/.env.example`
- Modify: `README.md` (the backend setup section, around the existing `.env` block)

- [ ] **Step 1: Add the new env vars to .env.example**

Append to `backend-app/.env.example`:

```
# Database (default targets the container volume; for local dev use a local file)
POLINGO_DATABASE_URL=sqlite:///./polingo.db
# LLM model ids (override to A/B models without code changes)
POLINGO_TEXT_MODEL=gpt-5-mini
POLINGO_STT_MODEL=whisper-1
POLINGO_TTS_MODEL=tts-1
POLINGO_TTS_VOICE=nova
```

- [ ] **Step 2: Document local-run DB override in README**

In `README.md`, in the "Backend setup" section, after the `.env` block (around line 38), add:

```markdown
> **Local (non-Docker) runs:** the default `POLINGO_DATABASE_URL` points at the
> container path `/app/data/polingo.db`. For a local run, set
> `POLINGO_DATABASE_URL=sqlite:///./polingo.db` in your `.env`.

### Running tests
```bash
cd backend-app
python -m pip install -r requirements.txt
python -m pytest
```
```

- [ ] **Step 3: Verify tests still pass and the app imports**

Run: `python -m pytest -v`
Expected: PASS.
Run: `python -c "import main; print('import ok')"`
Expected: prints `import ok`.

- [ ] **Step 4: Commit**

```bash
git add backend-app/.env.example README.md
git commit -m "docs: document POLINGO_* env vars and test command"
```

---

## Self-review

**Spec coverage (against the consolidated critique's "top 3 first moves" and Plan-1 scope):**
- M9 (SQLite `timeout: 30`) → Task 2, `make_engine`. ✓
- B3 (fail-loud migration) → Task 2, `_migrate_add_columns` re-raises non-duplicate errors. ✓ (Full Alembic adoption deferred to Plan 2, stated in header.)
- Hard-coded model ids → Task 3. ✓
- M2 (LLM answer-persist ratchet) → Task 4. ✓
- B2 + M10 (accusative/nominative plural virility) → Task 5. ✓
- Config/DB-path local-run fix → Tasks 1, 2, 6. ✓
- Test harness for TDD → Task 2. ✓
- B1 (virility *schema* axis), unified `Attempt`, ARQ, exercise engine, MCP, frontend, promptfoo → explicitly out of scope, assigned to later plans. ✓

**Placeholder scan:** No TBD/TODO/"add error handling"/"write tests for the above". Every code and test step shows full content. ✓

**Type/name consistency:** `make_engine(url)`, `config.database_url()/text_model()/stt_model()/tts_model()/tts_voice()`, `_migrate_add_columns(engine)`, and `init_db()` names are used identically across Tasks 1–3 and the tests. The `fresh_db`/`client`/`fake_llm` fixtures defined in Task 2 are consumed by Tasks 4 (`client`, re-monkeypatching `llm`) consistently. ✓

> **Note on Step 3 of Task 1:** the first `pytest.ini` shown uses an unsupported `[pytest:env]` block as an illustration; the actual file to create is the minimal one immediately below it. Env is set in `conftest.py` (Task 2), which is the working mechanism.
