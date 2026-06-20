# Polingo Schema Unification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Horizontal execution — Lane L1 (CRITICAL PATH).** This plan runs concurrently with L2 (frontend refactor), L3 (contract-freeze tests), and L4 (MCP/worker). See `2026-06-20-horizontal-execution-map.md` for the lane DAG and merge order. **Branch:** `plan-2-schema` in an isolated worktree. **Merge order:** 2nd (after L3 contract tests, before L2/L4).
>
> **Owned files (this lane only):** all `backend-app/app/*.py`, `backend-app/migrations/**`, `backend-app/requirements.txt`, `backend-app/tests/test_migrations.py`, `backend-app/tests/test_models_virility.py`, `backend-app/tests/test_attempt_unification.py`. **Do NOT** touch `frontend-app/**`, `mcp_server/**`, `worker/**`, or `backend-app/tests/contract/**` (other lanes own those). **Do NOT** edit `backend-app/tests/conftest.py` beyond what existing Plan 1 tests require — L3 adds its fixtures under `tests/contract/conftest.py`.
>
> **Contract delta you introduce (consumers absorb on rebase):** pronoun `oni/one` → `oni`+`one`; gender `męski` → 5-gender set; history record `id` becomes the real `Attempt.id`. These are catalogued in the execution map; no action needed here beyond shipping them.

**Goal:** Adopt Alembic for real schema migrations, add the virility axis (B1) via a 5-gender model plus an `oni`/`one` pronoun split, add a nullable `aspect` field to `Word`, and replace the two disjoint practice-result tables with a single `Attempt` table (M3) — migrating existing data losslessly.

**Architecture:** SQLModel `str` enums are stored as plain `VARCHAR` in SQLite with **no CHECK constraint** (verified), so widening `GrammaticalGender` (3→5) and splitting `Pronoun` are pure *data + code* changes — no column-type DDL. We introduce Alembic and make `init_db()` run `alembic upgrade head` on file databases (existing pre-Alembic DBs are `stamp`ed at the baseline first); in-memory test DBs keep building straight from model metadata, and the migrations themselves are tested against a temp file DB. The `Attempt` table is a superset of both old record tables with nullable context columns and a `kind` discriminator; a migration copies both tables into it and drops them in one step.

**Tech Stack:** Python 3.11+, FastAPI, SQLModel/SQLAlchemy 2.x, Alembic, SQLite, pytest.

**Depends on:** Plan 1 (env config seam `app.config`, pytest harness in `tests/conftest.py`, `make_engine`). Plan 1 must be merged or present on the branch.

**Out of scope (later plans):** populating `aspect` data and aspect/agreement/government exercises (Plan 4), the Topic×Format engine (Plan 4), ARQ form-gen (Plan 3), regenerating the `one` (non-virile) past-tense forms and full 5-gender adjective declension breadth (Plan 4 form-gen), MCP (Plan 5), frontend (Plan 6), promptfoo (Plan 7).

---

## Design decisions (locked with the user, 2026-06-18)

1. **Virility = full 5-gender model.** Replace `GrammaticalGender {męski, żeński, nijaki}` with `{męskoosobowy, męskozywotny, męskorzeczowy, żeński, nijaki}`. Virility is **derived** (`męskoosobowy` is the only virile gender), exposed via an `is_virile()` helper — not a separate column. Separately, split `Pronoun.oni_one` → `Pronoun.oni` (virile) + `Pronoun.one` (non-virile) so `oni robili` / `one robiły` can both be stored.
2. **Lossy gender remap is accepted.** Existing rows with `gender = "męski"` cannot have their animacy inferred, so they migrate to `męskorzeczowy` (inanimate — statistically most common). **Precise damage until re-tagging:** misclassified *animate* masculines (e.g. *pies*, *kot* → should be `męskozywotny`) get a wrong accusative **singular** (served *kot* instead of the animate *kota* = genitive); misclassified *personal* masculines (e.g. *student* → should be `męskoosobowy`) get a wrong accusative singular *and* wrong accusative-**plural**/virile agreement (served non-virile *koty/dobre* instead of *studentów/dobrzy*). Genitive/instrumental/locative are unaffected. Re-tagging masculine-personal/animate words is a documented follow-up, not part of this plan.
3. **`one` forms are handled per tense.** Existing `pronoun = "oni/one"` conjugation rows are *relabelled* to `oni`. Because **present and future** are morphologically identical for virile/non-virile, migration `0003` *duplicates* those rows as `one` so a query by `pronoun = "one"` is never empty there. **Past tense** genuinely differs (*robili* vs *robiły*) and is NOT fabricated — the `one` past form stays absent until form-gen regenerates it (later plan); callers must tolerate a missing `one` past row.
4. **Add `aspect` now, populate later.** A nullable `aspect` enum column is added to `Word` in this plan; data population and aspect exercises are Plan 4.
5. **Drop old tables in the copy migration.** After `Attempt` rows are copied, `practicerecord` and `endingspracticerecord` are dropped in the same migration. Single source of truth is enforced immediately.
6. **`Attempt` preserves existing stat semantics.** `get_words_with_stats` error-rate ordering counted only `PracticeRecord`; after unification it counts `Attempt` rows with `kind == "practice"`. Broadening it to include endings is a future product decision, deliberately not made here.

---

## File structure

| File | Responsibility | Status |
|---|---|---|
| `backend-app/requirements.txt` | Add `alembic`. | Modify |
| `backend-app/alembic.ini` | Alembic config: script location, `prepend_sys_path = .`. | Create |
| `backend-app/migrations/env.py` | Alembic env: target metadata = `SQLModel.metadata`, URL from `app.config`, `render_as_batch=True` (SQLite). | Create |
| `backend-app/migrations/script.py.mako` | Standard revision template. | Create |
| `backend-app/migrations/versions/0001_baseline.py` | Baseline = current schema (autogenerated, then pinned `revision="0001_baseline"`). | Create |
| `backend-app/migrations/versions/0002_gender_five_way.py` | Data: remap `męski` → `męskorzeczowy` in `word` + `worddeclension`. | Create |
| `backend-app/migrations/versions/0003_pronoun_virility.py` | Data: relabel `oni/one` → `oni` in `verbconjugation`. | Create |
| `backend-app/migrations/versions/0004_word_aspect.py` | DDL: add nullable `aspect` column to `word`. | Create |
| `backend-app/migrations/versions/0005_attempt_table.py` | DDL: create `attempt` table + indexes. | Create |
| `backend-app/migrations/versions/0006_attempt_data_and_drop.py` | Data+DDL: copy both record tables into `attempt`, drop them. | Create |
| `backend-app/app/database.py` | Replace `create_all`/`_migrate_add_columns` with Alembic-driven `run_migrations()`. | Modify |
| `backend-app/app/models.py` | 5-gender enum + `is_virile`; `oni`/`one`; `Aspect` + `Word.aspect`; `AttemptKind` + `Attempt`; delete old record models. | Modify |
| `backend-app/app/llm.py` | Update resolve prompt (5 genders + aspect) and conjugation prompt (`oni`/`one` + virile past-tense note). | Modify |
| `backend-app/app/api/words.py` | `PRONOUN_MAP` `oni`/`one`; defensive legacy-gender mapping; store `aspect` on new `Word`s. | Modify |
| `backend-app/app/api/practice.py` | Write `Attempt(kind=practice, …)` at the 5 record sites. | Modify |
| `backend-app/app/api/endings.py` | Write/read `Attempt(kind=endings, …)`. | Modify |
| `backend-app/app/api/stats.py` | History from a single `Attempt` query. | Modify |
| `backend-app/app/utils.py` | `calculate_stats` from `Attempt`. | Modify |
| `backend-app/app/api/session.py` | Cascade-delete + error-rate subquery use `Attempt`. | Modify |
| `backend-app/tests/test_migrations.py` | Alembic upgrade against a temp file DB; data-preservation assertions. | Create |
| `backend-app/tests/test_models_virility.py` | 5-gender enum, `is_virile`, `oni`/`one`, `Aspect`. | Create |
| `backend-app/tests/test_attempt_unification.py` | Endpoints write/read `Attempt`; stats/history preserved. | Create |

> All commands assume working directory `backend-app/`. Use the project venv: `.venv/bin/python` and `.venv/bin/pytest` / `.venv/bin/alembic`. Run `.venv/bin/python -m pip install -r requirements.txt` once after Task 1, Step 1.

---

### Task 1: Introduce Alembic and a baseline migration

**Files:**
- Modify: `backend-app/requirements.txt`
- Create: `backend-app/alembic.ini`, `backend-app/migrations/env.py`, `backend-app/migrations/script.py.mako`, `backend-app/migrations/versions/0001_baseline.py`
- Modify: `backend-app/app/database.py:62-79` (`init_db`) and add `run_migrations`
- Create: `backend-app/tests/test_migrations.py`

- [ ] **Step 1: Add alembic to requirements and install**

Append to `backend-app/requirements.txt`:

```
alembic>=1.13
```

Run: `.venv/bin/python -m pip install -r requirements.txt`
Expected: alembic installs.

- [ ] **Step 2: Create `alembic.ini`**

Create `backend-app/alembic.ini`:

```ini
[alembic]
script_location = migrations
prepend_sys_path = .
# URL is owned by env.py (_resolve_url) — resolved from the cfg or app.config at
# run time. Left blank deliberately so a bare `alembic` invocation cannot silently
# target the wrong database.
sqlalchemy.url =

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 3: Create `migrations/script.py.mako`**

Create `backend-app/migrations/script.py.mako`:

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 4: Create `migrations/env.py`**

Create `backend-app/migrations/env.py`. It reads the live DB URL from `app.config`, points Alembic at `SQLModel.metadata`, and turns on batch mode (required for SQLite ALTER/DROP).

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

from app import config as app_config
from app import models  # noqa: F401  -- import so every table registers on the metadata

alembic_config = context.config

if alembic_config.config_file_name is not None:
    fileConfig(alembic_config.config_file_name)

target_metadata = SQLModel.metadata


def _resolve_url() -> str:
    # Resolve at run time, not import time: a caller (test/runtime) may have set
    # POLINGO_DATABASE_URL or sqlalchemy.url on the cfg after env.py was imported.
    return alembic_config.get_main_option("sqlalchemy.url") or app_config.database_url()


def run_migrations_offline() -> None:
    context.configure(
        url=_resolve_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = dict(alembic_config.get_section(alembic_config.config_ini_section, {}))
    section["sqlalchemy.url"] = _resolve_url()
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 5: Autogenerate the baseline against an empty database**

The baseline must capture **today's** schema, so do this *before* editing any models. Autogenerate compares the models to an empty DB, emitting `create_table` for every current table.

Run:
```bash
rm -f _gen_baseline.db
POLINGO_DATABASE_URL="sqlite:///./_gen_baseline.db" .venv/bin/alembic revision --autogenerate -m baseline
rm -f _gen_baseline.db
```
Expected: a new file under `migrations/versions/` containing `op.create_table(...)` for `word`, `wordoption`, `worddeclension`, `verbconjugation`, `practicesentence`, `usersession`, `usersessionword`, `practicerecord`, `endingspracticerecord`, `appsetting`, `connecteddevice`.

- [ ] **Step 6: Pin the baseline revision id**

Rename the generated file to `backend-app/migrations/versions/0001_baseline.py` and edit its header so the id is stable and it is the root:

```python
revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None
```

Leave the autogenerated `upgrade()`/`downgrade()` bodies as-is. Verify it still includes `practicerecord` and `endingspracticerecord` create_table calls (later migrations drop them).

> **Known follow-up (not blocking):** the models' `UniqueConstraint`s are unnamed, so a *future* `--autogenerate` (Plan 3+) may emit spurious drop/re-add diffs for them. This plan only hand-authors migrations after the baseline, so it is unaffected. Naming those constraints (`name="uq_…"`) is a cheap cleanup to do before any future autogenerate workflow.

- [ ] **Step 7: Write the failing migration test**

Create `backend-app/tests/test_migrations.py`:

```python
import pathlib
import sqlite3

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig

_BACKEND_ROOT = pathlib.Path(__file__).resolve().parent.parent  # backend-app/


def _alembic_cfg(db_path: str) -> AlembicConfig:
    # Absolute paths so the test passes regardless of pytest's working directory.
    cfg = AlembicConfig(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return cfg


# xfail until Task 6 adds the final migrations — keeps the suite green for the
# intermediate commits. The marker is REMOVED in Task 6, Step 1.
@pytest.mark.xfail(reason="attempt table + table drop land in Task 6", strict=True)
def test_upgrade_head_builds_attempt_and_drops_old_tables(tmp_path, monkeypatch):
    db = tmp_path / "mig.db"
    monkeypatch.setenv("POLINGO_DATABASE_URL", f"sqlite:///{db}")
    command.upgrade(_alembic_cfg(str(db)), "head")

    con = sqlite3.connect(db)
    names = {r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    con.close()

    assert "attempt" in names
    assert "practicerecord" not in names
    assert "endingspracticerecord" not in names
```

- [ ] **Step 8: Run it to confirm it xfails (not errors)**

Run: `.venv/bin/pytest tests/test_migrations.py -v`
Expected: `1 xfailed` — only `0001_baseline` exists, so `attempt` is absent and the old tables are still present; the `xfail` marker keeps the suite green.

> This test is the acceptance test for the whole plan; it stays `xfail` until Task 6 removes the marker. Tasks 2–5 add their own green tests, so every intermediate commit has a fully green suite.

- [ ] **Step 9: Re-point `init_db` at Alembic**

In `backend-app/app/database.py`, **delete** `_migrate_add_columns` (lines 35-59) and replace the imports block + `init_db` so migrations drive the schema. Replace lines `1-13`:

```python
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import inspect
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app import config
from app.models import AppSetting, UserSession, Word
from app.seed import seed_words

logger = logging.getLogger("polingo.database")

_MEMORY_URLS = {"sqlite://", "sqlite:///:memory:"}
_ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"
```

Then replace `init_db` (now at lines 62-79 after deleting `_migrate_add_columns`) with:

```python
def _alembic_config() -> AlembicConfig:
    cfg = AlembicConfig(str(_ALEMBIC_INI))
    cfg.set_main_option("script_location", str(_ALEMBIC_INI.parent / "migrations"))
    cfg.set_main_option("sqlalchemy.url", config.database_url())
    return cfg


def run_migrations() -> None:
    """Bring the schema to head. In-memory DBs (tests) are built directly from
    model metadata — Alembic is exercised against a file DB in test_migrations.
    Pre-Alembic file DBs (built by the old create_all path) are stamped at the
    baseline before upgrading so their existing data is preserved."""
    url = config.database_url()
    if url in _MEMORY_URLS:
        SQLModel.metadata.create_all(engine)
        return
    cfg = _alembic_config()
    # Inspect the same physical DB Alembic will target (build a throwaway engine
    # from the resolved URL rather than reusing the module engine).
    insp_engine = create_engine(url)
    try:
        tables = set(inspect(insp_engine).get_table_names())
    finally:
        insp_engine.dispose()
    if "alembic_version" not in tables and "word" in tables:
        command.stamp(cfg, "0001_baseline")
    command.upgrade(cfg, "head")


def init_db() -> None:
    run_migrations()
    with Session(engine) as session:
        has_words = session.exec(select(Word)).first()
        if not has_words:
            seed_words(session)
        has_session = session.exec(select(UserSession)).first()
        if not has_session:
            session.add(UserSession())
            session.commit()
        if not session.get(AppSetting, "generate_on_the_fly"):
            session.add(AppSetting(key="generate_on_the_fly", value="false"))
            session.commit()
        if not session.get(AppSetting, "tts_source"):
            session.add(AppSetting(key="tts_source", value="browser"))
            session.commit()
```

> Keep `make_engine` and the module-level `engine = make_engine(config.database_url())` exactly as they are. `get_session()` is unchanged.

- [ ] **Step 10: Run the existing suite to confirm nothing regressed**

Run: `.venv/bin/pytest -v`
Expected: all Plan 1 tests still pass; `tests/test_migrations.py` reports `1 xfailed` (the acceptance test), suite green overall. The Plan 1 `test_migration_is_idempotent_on_memory` passes because in-memory `init_db()` now calls `create_all` twice idempotently.

- [ ] **Step 11: Commit**

```bash
git add backend-app/requirements.txt backend-app/alembic.ini backend-app/migrations backend-app/app/database.py backend-app/tests/test_migrations.py
git commit -m "feat: adopt Alembic; baseline migration; init_db runs upgrade head (B3)"
```

---

### Task 2: Expand GrammaticalGender to the 5-gender model (B1, part 1)

**Files:**
- Modify: `backend-app/app/models.py:45-48`
- Create: `backend-app/migrations/versions/0002_gender_five_way.py`
- Modify: `backend-app/app/llm.py:35` (resolve gender vocab) and `:196` (adjective declension gender vocab)
- Modify: `backend-app/app/api/words.py:60-61` (defensive legacy-gender mapping)
- Create: `backend-app/tests/test_models_virility.py`

- [ ] **Step 1: Write the failing model test**

Create `backend-app/tests/test_models_virility.py`:

```python
from app.models import GrammaticalGender, is_animate_masculine, is_virile


def test_gender_has_five_members():
    assert {g.value for g in GrammaticalGender} == {
        "męskoosobowy", "męskozywotny", "męskorzeczowy", "żeński", "nijaki",
    }


def test_is_virile_only_true_for_meskoosobowy():
    assert is_virile(GrammaticalGender.meskoosobowy) is True
    assert is_virile("męskoosobowy") is True
    assert is_virile(GrammaticalGender.meskozywotny) is False
    assert is_virile(GrammaticalGender.zenski) is False
    assert is_virile(None) is False


def test_is_animate_masculine_covers_both_masc_animate_genders():
    assert is_animate_masculine(GrammaticalGender.meskoosobowy) is True
    assert is_animate_masculine(GrammaticalGender.meskozywotny) is True
    assert is_animate_masculine(GrammaticalGender.meskorzeczowy) is False
    assert is_animate_masculine(GrammaticalGender.zenski) is False
    assert is_animate_masculine(None) is False
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/bin/pytest tests/test_models_virility.py -v`
Expected: FAIL — `ImportError: cannot import name 'is_virile'` / enum has 3 members.

- [ ] **Step 3: Rewrite the enum and add the helper**

In `backend-app/app/models.py`, replace the `GrammaticalGender` class (lines 45-48):

```python
class GrammaticalGender(str, Enum):
    meskoosobowy = "męskoosobowy"      # masculine personal (virile)
    meskozywotny = "męskozywotny"      # masculine animate (non-personal)
    meskorzeczowy = "męskorzeczowy"    # masculine inanimate
    zenski = "żeński"
    nijaki = "nijaki"


def is_virile(gender) -> bool:
    """True only for męskoosobowy — the gender that drives virile PLURAL
    agreement and the accusative-PLURAL=genitive-plural rule (B1).

    NOTE: this is a plural-only distinction. It does NOT govern the accusative
    SINGULAR, which follows animacy: both męskoosobowy AND męskozywotny take
    Acc.Sg = Gen.Sg (kota, psa). Use is_animate_masculine() for singular."""
    if gender is None:
        return False
    value = gender.value if isinstance(gender, GrammaticalGender) else str(gender)
    return value == GrammaticalGender.meskoosobowy.value


def is_animate_masculine(gender) -> bool:
    """True for męskoosobowy and męskozywotny — the genders whose accusative
    SINGULAR equals the genitive singular (widzę kota/studenta, not *kot)."""
    if gender is None:
        return False
    value = gender.value if isinstance(gender, GrammaticalGender) else str(gender)
    return value in {
        GrammaticalGender.meskoosobowy.value,
        GrammaticalGender.meskozywotny.value,
    }
```

- [ ] **Step 4: Run the model test to confirm it passes**

Run: `.venv/bin/pytest tests/test_models_virility.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Write the data migration**

Create `backend-app/migrations/versions/0002_gender_five_way.py`:

```python
"""remap masculine gender to the 5-gender model

Revision ID: 0002_gender_five_way
Revises: 0001_baseline
"""
from alembic import op

revision = "0002_gender_five_way"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Legacy "męski" carried no animacy; default to inanimate (most common).
    op.execute("UPDATE worddeclension SET gender = 'męskorzeczowy' WHERE gender = 'męski'")
    op.execute("UPDATE word SET gender = 'męskorzeczowy' WHERE gender = 'męski'")


def downgrade() -> None:
    op.execute(
        "UPDATE worddeclension SET gender = 'męski' "
        "WHERE gender IN ('męskoosobowy', 'męskozywotny', 'męskorzeczowy')"
    )
    op.execute(
        "UPDATE word SET gender = 'męski' "
        "WHERE gender IN ('męskoosobowy', 'męskozywotny', 'męskorzeczowy')"
    )
```

- [ ] **Step 6: Extend the migration test to prove the remap**

Append to `backend-app/tests/test_migrations.py`:

```python
def test_gender_remap_defaults_legacy_meski_to_inanimate(tmp_path, monkeypatch):
    db = tmp_path / "gender.db"
    monkeypatch.setenv("POLINGO_DATABASE_URL", f"sqlite:///{db}")
    cfg = _alembic_cfg(str(db))
    command.upgrade(cfg, "0001_baseline")

    con = sqlite3.connect(db)
    con.execute("INSERT INTO word (polish, english, ukrainian, part_of_speech, gender) "
                "VALUES ('kot', 'cat', 'кіт', 'rzeczownik', 'męski')")
    con.commit()
    con.close()

    command.upgrade(cfg, "0002_gender_five_way")

    con = sqlite3.connect(db)
    gender = con.execute("SELECT gender FROM word WHERE polish='kot'").fetchone()[0]
    con.close()
    assert gender == "męskorzeczowy"
```

- [ ] **Step 7: Run the migration test**

Run: `.venv/bin/pytest tests/test_migrations.py::test_gender_remap_defaults_legacy_meski_to_inanimate -v`
Expected: PASS.

- [ ] **Step 8: Update the LLM prompts to use the 5-gender vocabulary**

In `backend-app/app/llm.py`, replace the gender clause on line 35:

```python
        "gender (for rzeczownik only: one of męskoosobowy [masc. personal], "
        "męskozywotny [masc. animate], męskorzeczowy [masc. inanimate], żeński, "
        "or nijaki; null otherwise). "
```

And replace the adjective gender clause on line 196:

```python
            "miejscownik, wołacz) for all five genders (męskoosobowy, męskozywotny, "
            "męskorzeczowy, żeński, nijaki) "
```

- [ ] **Step 9: Add defensive legacy-gender mapping in form generation**

In `backend-app/app/api/words.py`, in `_generate_forms_background`, after the line `gender_val = f.get("gender", gender or "")` (line 61), insert:

```python
                    if gender_val == "męski":
                        gender_val = "męskorzeczowy"  # legacy value safety net
```

(This guards against an old word/LLM response still emitting the bare `męski`, which would otherwise raise `ValueError` in `GrammaticalGender(gender_val)` and silently skip the form.)

- [ ] **Step 10: Run the full suite**

Run: `.venv/bin/pytest -v`
Expected: all green; `test_upgrade_head_builds_attempt_and_drops_old_tables` reports `xfailed` (expected until Task 6).

- [ ] **Step 11: Commit**

```bash
git add backend-app/app/models.py backend-app/migrations/versions/0002_gender_five_way.py backend-app/app/llm.py backend-app/app/api/words.py backend-app/tests/test_models_virility.py backend-app/tests/test_migrations.py
git commit -m "feat: 5-gender model with is_virile; remap legacy męski (B1)"
```

---

### Task 3: Split the Pronoun enum into oni/one (B1, part 2)

**Files:**
- Modify: `backend-app/app/models.py:62-68`
- Modify: `backend-app/app/api/words.py:41-48` (`PRONOUN_MAP`)
- Modify: `backend-app/app/llm.py:154` (conjugation prompt)
- Create: `backend-app/migrations/versions/0003_pronoun_virility.py`
- Modify: `backend-app/tests/test_models_virility.py`

- [ ] **Step 1: Write the failing test**

Append to `backend-app/tests/test_models_virility.py`:

```python
from app.models import Pronoun


def test_pronoun_splits_oni_one():
    values = {p.value for p in Pronoun}
    assert "oni" in values
    assert "one" in values
    assert "oni/one" not in values
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/bin/pytest tests/test_models_virility.py::test_pronoun_splits_oni_one -v`
Expected: FAIL — `oni/one` still present, `oni`/`one` absent.

- [ ] **Step 3: Rewrite the Pronoun enum**

In `backend-app/app/models.py`, replace the `Pronoun` class (lines 62-68):

```python
class Pronoun(str, Enum):
    ja = "ja"
    ty = "ty"
    on_ona_ono = "on/ona/ono"
    my = "my"
    wy = "wy"
    oni = "oni"   # męskoosobowy (virile) plural — "oni robili"
    one = "one"   # niemęskoosobowy (non-virile) plural — "one robiły"
```

- [ ] **Step 4: Update PRONOUN_MAP**

In `backend-app/app/api/words.py`, replace `PRONOUN_MAP` (lines 41-48):

```python
PRONOUN_MAP = {
    "ja": Pronoun.ja,
    "ty": Pronoun.ty,
    "on_ona_ono": Pronoun.on_ona_ono,
    "my": Pronoun.my,
    "wy": Pronoun.wy,
    "oni": Pronoun.oni,
    "one": Pronoun.one,
}
```

- [ ] **Step 5: Update the conjugation prompt**

In `backend-app/app/llm.py`, replace the pronoun-keys line (line 154) and the past-tense instruction (line 156-157) inside `generate_verb_conjugations_via_llm`:

```python
        "and each value is an object with pronoun keys (ja, ty, on_ona_ono, my, wy, oni, one) "
        "mapping to the conjugated Polish form. "
        "For past tense, use masculine forms for ja/ty/on and feminine for ona; "
        "'oni' is the męskoosobowy (virile) plural form (e.g. robili) and 'one' is the "
        "niemęskoosobowy (non-virile) plural form (e.g. robiły). "
        "For present and future tense, 'oni' and 'one' take IDENTICAL forms — return the "
        "same conjugated form under both keys (e.g. oni robią / one robią). "
        # TODO (M5): for dokonany (perfective) verbs the future is synthetic, never
        # the compound 'będzie + infinitive'; aspect-aware validation lands in a later plan.
```

- [ ] **Step 6: Write the data migration**

Create `backend-app/migrations/versions/0003_pronoun_virility.py`:

```python
"""relabel oni/one conjugations to the virile oni form

Revision ID: 0003_pronoun_virility
Revises: 0002_gender_five_way
"""
from alembic import op

revision = "0003_pronoun_virility"
down_revision = "0002_gender_five_way"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing "oni/one" forms map to the virile "oni".
    op.execute("UPDATE verbconjugation SET pronoun = 'oni' WHERE pronoun = 'oni/one'")
    # Present/future are identical for oni/one, so duplicate those rows as "one"
    # to avoid an empty result on pronoun='one' queries. Past tense differs
    # (robili vs robiły) and is left for form-gen to regenerate — not fabricated.
    op.execute(
        "INSERT INTO verbconjugation (word_id, pronoun, tense, conjugated_form) "
        "SELECT word_id, 'one', tense, conjugated_form FROM verbconjugation "
        "WHERE pronoun = 'oni' AND tense IN ('teraźniejszy', 'przyszły')"
    )


def downgrade() -> None:
    op.execute("DELETE FROM verbconjugation WHERE pronoun = 'one'")
    op.execute("UPDATE verbconjugation SET pronoun = 'oni/one' WHERE pronoun = 'oni'")
```

- [ ] **Step 7: Extend the migration test**

Append to `backend-app/tests/test_migrations.py`:

```python
def test_pronoun_relabel_oni_one_to_oni(tmp_path, monkeypatch):
    db = tmp_path / "pron.db"
    monkeypatch.setenv("POLINGO_DATABASE_URL", f"sqlite:///{db}")
    cfg = _alembic_cfg(str(db))
    command.upgrade(cfg, "0002_gender_five_way")

    con = sqlite3.connect(db)
    con.execute("INSERT INTO word (polish, english, ukrainian, part_of_speech) "
                "VALUES ('robić', 'to do', 'робити', 'czasownik')")
    wid = con.execute("SELECT id FROM word WHERE polish='robić'").fetchone()[0]
    con.execute("INSERT INTO verbconjugation (word_id, pronoun, tense, conjugated_form) "
                "VALUES (?, 'oni/one', 'przeszły', 'robili')", (wid,))
    con.execute("INSERT INTO verbconjugation (word_id, pronoun, tense, conjugated_form) "
                "VALUES (?, 'oni/one', 'teraźniejszy', 'robią')", (wid,))
    con.commit()
    con.close()

    command.upgrade(cfg, "0003_pronoun_virility")

    con = sqlite3.connect(db)
    # past-tense row relabelled to virile oni, NOT duplicated as one
    past = con.execute("SELECT pronoun FROM verbconjugation "
                       "WHERE word_id=? AND tense='przeszły'", (wid,)).fetchall()
    # present-tense row relabelled to oni AND duplicated as one
    present = {r[0] for r in con.execute(
        "SELECT pronoun FROM verbconjugation WHERE word_id=? AND tense='teraźniejszy'",
        (wid,)).fetchall()}
    con.close()
    assert past == [("oni",)]
    assert present == {"oni", "one"}
```

- [ ] **Step 8: Run the new tests**

Run: `.venv/bin/pytest tests/test_models_virility.py tests/test_migrations.py::test_pronoun_relabel_oni_one_to_oni -v`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add backend-app/app/models.py backend-app/app/api/words.py backend-app/app/llm.py backend-app/migrations/versions/0003_pronoun_virility.py backend-app/tests/test_models_virility.py backend-app/tests/test_migrations.py
git commit -m "feat: split Pronoun oni/one for virile past-tense storage (B1)"
```

---

### Task 4: Add the nullable aspect field to Word (M4/M5 groundwork)

**Files:**
- Modify: `backend-app/app/models.py` (add `Aspect` enum near the other enums; add `Word.aspect`)
- Create: `backend-app/migrations/versions/0004_word_aspect.py`
- Modify: `backend-app/app/llm.py:35,46-54` (resolve prompt + return dict)
- Modify: `backend-app/app/api/words.py:253-258,346-351,470-473` (store `aspect` on new `Word`s)
- Modify: `backend-app/tests/test_models_virility.py`

- [ ] **Step 1: Write the failing test**

Append to `backend-app/tests/test_models_virility.py`:

```python
from app.models import Aspect, Word


def test_aspect_enum_values():
    assert {a.value for a in Aspect} == {"dokonany", "niedokonany"}


def test_word_accepts_optional_aspect():
    w = Word(polish="zrobić", english="to do", ukrainian="зробити",
             part_of_speech="czasownik", aspect=Aspect.dokonany)
    assert w.aspect == Aspect.dokonany
    w2 = Word(polish="kot", english="cat", ukrainian="кіт", part_of_speech="rzeczownik")
    assert w2.aspect is None
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/bin/pytest tests/test_models_virility.py::test_aspect_enum_values -v`
Expected: FAIL — `cannot import name 'Aspect'`.

- [ ] **Step 3: Add the Aspect enum and Word.aspect column**

In `backend-app/app/models.py`, add the enum after `VerbTense` (after line 59):

```python
class Aspect(str, Enum):
    dokonany = "dokonany"        # perfective
    niedokonany = "niedokonany"  # imperfective
```

Then add the column to `Word` (after the `gender` field at line 80):

```python
    aspect: Optional[Aspect] = Field(default=None)  # for czasownik only (M4/M5)
```

- [ ] **Step 4: Run the model test**

Run: `.venv/bin/pytest tests/test_models_virility.py::test_aspect_enum_values tests/test_models_virility.py::test_word_accepts_optional_aspect -v`
Expected: PASS.

- [ ] **Step 5: Write the DDL migration**

Create `backend-app/migrations/versions/0004_word_aspect.py`:

```python
"""add nullable aspect column to word

Revision ID: 0004_word_aspect
Revises: 0003_pronoun_virility
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_word_aspect"
down_revision = "0003_pronoun_virility"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("word") as batch:
        batch.add_column(sa.Column("aspect", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("word") as batch:
        batch.drop_column("aspect")
```

- [ ] **Step 6: Extend the migration test**

Append to `backend-app/tests/test_migrations.py`:

```python
def test_word_has_aspect_column_after_upgrade(tmp_path, monkeypatch):
    db = tmp_path / "aspect.db"
    monkeypatch.setenv("POLINGO_DATABASE_URL", f"sqlite:///{db}")
    cfg = _alembic_cfg(str(db))
    command.upgrade(cfg, "0004_word_aspect")

    con = sqlite3.connect(db)
    cols = {r[1] for r in con.execute("PRAGMA table_info(word)").fetchall()}
    con.close()
    assert "aspect" in cols
```

- [ ] **Step 7: Update the resolve prompt and return dict**

In `backend-app/app/llm.py`, in `resolve_word_via_llm`, append to the prompt (after the gender clause, before `"Use lowercase..."`):

```python
        "aspect (for czasownik only: dokonany or niedokonany; null otherwise). "
```

And add `aspect` to the returned dict (after the `"gender"` key at line 53):

```python
        "aspect": payload.get("aspect"),
```

- [ ] **Step 8: Store aspect on new Words**

In `backend-app/app/api/words.py` there are **three** `Word(...)` constructors that build a new word from `resolved` (near lines 253, 346, 470 — line numbers may have drifted, so match by content, not number). Each contains the line `gender=resolved.get("gender"),`. Add `aspect=resolved.get("aspect"),` immediately after it in all three. Because the exact `gender=resolved.get("gender"),` line is identical at every site, use a replace-all-style edit:

- old: `            gender=resolved.get("gender"),` (also appears as `ukrainian=resolved["ukrainian"], part_of_speech=pos_enum,\n                        gender=resolved.get("gender"),` in the bulk path — verify each occurrence is a `Word(...)` constructor before editing)
- new: the same line, followed by `            aspect=resolved.get("aspect"),`

After editing, confirm three insertions: `grep -c "aspect=resolved.get" backend-app/app/api/words.py` should print `3`.

> Do NOT confuse these with the `WordDeclension(... gender=gender_enum ...)` site or `PracticeSentence(... gender=s.get("gender") ...)` — those use different right-hand sides and must not gain an `aspect` line.

- [ ] **Step 9: Run the full suite**

Run: `.venv/bin/pytest -v`
Expected: green; the Task-6 acceptance test reports `xfailed`.

- [ ] **Step 10: Commit**

```bash
git add backend-app/app/models.py backend-app/migrations/versions/0004_word_aspect.py backend-app/app/llm.py backend-app/app/api/words.py backend-app/tests/test_models_virility.py backend-app/tests/test_migrations.py
git commit -m "feat: add nullable Word.aspect (M4/M5 groundwork)"
```

---

### Task 5: Create the unified Attempt table

**Files:**
- Modify: `backend-app/app/models.py` (add `AttemptKind` + `Attempt`; keep old record models for now)
- Create: `backend-app/migrations/versions/0005_attempt_table.py`
- Modify: `backend-app/tests/test_migrations.py`

- [ ] **Step 1: Write the failing test**

Append to `backend-app/tests/test_migrations.py`:

```python
def test_attempt_table_created_at_0005(tmp_path, monkeypatch):
    db = tmp_path / "att.db"
    monkeypatch.setenv("POLINGO_DATABASE_URL", f"sqlite:///{db}")
    cfg = _alembic_cfg(str(db))
    command.upgrade(cfg, "0005_attempt_table")

    con = sqlite3.connect(db)
    names = {r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    cols = {r[1] for r in con.execute("PRAGMA table_info(attempt)").fetchall()}
    con.close()

    assert "attempt" in names
    # old tables still present at this revision (dropped in 0006)
    assert "practicerecord" in names and "endingspracticerecord" in names
    assert {"word_id", "kind", "language_set", "direction", "part_of_speech",
            "was_correct", "user_answer", "correct_answer", "practice_date",
            "created_at"} <= cols
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/bin/pytest tests/test_migrations.py::test_attempt_table_created_at_0005 -v`
Expected: FAIL — revision `0005_attempt_table` does not exist.

- [ ] **Step 3: Add the Attempt model**

In `backend-app/app/models.py`, add after the `EndingsPracticeRecord` class (after line 178). `AttemptKind` discriminates origin so history's "section" and the practice-only error-rate query can be reconstructed.

```python
class AttemptKind(str, Enum):
    practice = "practice"   # translation / writing / pronunciation
    endings = "endings"     # grammar endings practice


class Attempt(SQLModel, table=True):
    """Single source of truth for one graded answer (M3). Supersedes the
    disjoint PracticeRecord + EndingsPracticeRecord tables."""
    id: Optional[int] = Field(default=None, primary_key=True)
    word_id: int = Field(foreign_key="word.id", index=True)
    kind: AttemptKind = Field(index=True)
    language_set: Optional[LanguageSet] = Field(default=None)
    direction: Optional[PracticeDirection] = Field(default=None)
    part_of_speech: Optional[PartOfSpeech] = Field(default=None)
    was_correct: bool
    user_answer: Optional[str] = Field(default=None)
    correct_answer: Optional[str] = Field(default=None)
    practice_date: date = Field(default_factory=date.today, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

- [ ] **Step 4: Write the create-table migration**

Create `backend-app/migrations/versions/0005_attempt_table.py`:

```python
"""create unified attempt table

Revision ID: 0005_attempt_table
Revises: 0004_word_aspect
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_attempt_table"
down_revision = "0004_word_aspect"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "attempt",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("word_id", sa.Integer(), sa.ForeignKey("word.id"), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("language_set", sa.String(), nullable=True),
        sa.Column("direction", sa.String(), nullable=True),
        sa.Column("part_of_speech", sa.String(), nullable=True),
        sa.Column("was_correct", sa.Boolean(), nullable=False),
        sa.Column("user_answer", sa.String(), nullable=True),
        sa.Column("correct_answer", sa.String(), nullable=True),
        sa.Column("practice_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_attempt_word_id", "attempt", ["word_id"])
    op.create_index("ix_attempt_kind", "attempt", ["kind"])
    op.create_index("ix_attempt_practice_date", "attempt", ["practice_date"])


def downgrade() -> None:
    op.drop_index("ix_attempt_practice_date", table_name="attempt")
    op.drop_index("ix_attempt_kind", table_name="attempt")
    op.drop_index("ix_attempt_word_id", table_name="attempt")
    op.drop_table("attempt")
```

- [ ] **Step 5: Run the migration test**

Run: `.venv/bin/pytest tests/test_migrations.py::test_attempt_table_created_at_0005 -v`
Expected: PASS.

- [ ] **Step 6: Run the full suite**

Run: `.venv/bin/pytest -v`
Expected: green; the Task-6 acceptance test reports `xfailed`.

- [ ] **Step 7: Commit**

```bash
git add backend-app/app/models.py backend-app/migrations/versions/0005_attempt_table.py backend-app/tests/test_migrations.py
git commit -m "feat: add unified Attempt model + create-table migration (M3)"
```

---

### Task 6: Cut over to Attempt — copy data, drop old tables, rewrite call sites

**Background:** This is the atomic cutover. One migration copies both record tables into `attempt` then drops them; in the same commit every read/write site switches to `Attempt` and the old models are deleted, so the codebase and schema stay consistent. The single-user app tolerates the brief migration.

**Files:**
- Create: `backend-app/migrations/versions/0006_attempt_data_and_drop.py`
- Modify: `backend-app/app/utils.py:8,12-49`
- Modify: `backend-app/app/api/stats.py:7,34-78`
- Modify: `backend-app/app/api/practice.py` (5 record sites: 16-23 imports, 42, 105-114, 151-160, 206-215, 330-339)
- Modify: `backend-app/app/api/endings.py` (validate at 357-363, `_calculate_endings_stats` at 381-408, imports)
- Modify: `backend-app/app/api/session.py:236-244` (cascade), `:46-56` (subquery), imports
- Modify: `backend-app/app/models.py` (delete `PracticeRecord` + `EndingsPracticeRecord`)
- Modify: `backend-app/tests/test_migrations.py` (remove the `xfail` marker; add the data-copy test)
- Create: `backend-app/tests/test_attempt_unification.py`

- [ ] **Step 1: Remove the xfail marker and write the data-migration test**

In `backend-app/tests/test_migrations.py`, delete the `@pytest.mark.xfail(...)` decorator above `test_upgrade_head_builds_attempt_and_drops_old_tables` (the migrations in this task make it pass; a strict xfail would otherwise XPASS-fail the suite).

Then append the data-copy test to `backend-app/tests/test_migrations.py`:

```python
def test_data_copied_into_attempt_then_old_tables_dropped(tmp_path, monkeypatch):
    db = tmp_path / "copy.db"
    monkeypatch.setenv("POLINGO_DATABASE_URL", f"sqlite:///{db}")
    cfg = _alembic_cfg(str(db))
    command.upgrade(cfg, "0005_attempt_table")

    con = sqlite3.connect(db)
    con.execute("INSERT INTO word (polish, english, ukrainian, part_of_speech) "
                "VALUES ('kot', 'cat', 'кіт', 'rzeczownik')")
    wid = con.execute("SELECT id FROM word WHERE polish='kot'").fetchone()[0]
    con.execute("INSERT INTO practicerecord (word_id, language_set, direction, was_correct, "
                "user_answer, correct_answer, practice_date, created_at) "
                "VALUES (?, 'english', 'writing', 1, 'kot', 'kot', '2026-06-18', '2026-06-18 10:00:00')", (wid,))
    con.execute("INSERT INTO endingspracticerecord (word_id, part_of_speech, was_correct, "
                "user_answer, correct_answer, practice_date, created_at) "
                "VALUES (?, 'rzeczownik', 0, 'kota', 'kotu', '2026-06-18', '2026-06-18 11:00:00')", (wid,))
    con.commit()
    con.close()

    command.upgrade(cfg, "head")

    con = sqlite3.connect(db)
    names = {r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    total = con.execute("SELECT COUNT(*) FROM attempt").fetchone()[0]
    practice = con.execute("SELECT COUNT(*) FROM attempt WHERE kind='practice'").fetchone()[0]
    endings = con.execute("SELECT COUNT(*) FROM attempt WHERE kind='endings'").fetchone()[0]
    con.close()

    assert total == 2 and practice == 1 and endings == 1
    assert "practicerecord" not in names and "endingspracticerecord" not in names
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/bin/pytest tests/test_migrations.py::test_data_copied_into_attempt_then_old_tables_dropped -v`
Expected: FAIL — revision `head` is still `0005`; old tables not dropped.

- [ ] **Step 3: Write the copy + drop migration**

Create `backend-app/migrations/versions/0006_attempt_data_and_drop.py`:

```python
"""copy practice/endings records into attempt, drop old tables

Revision ID: 0006_attempt_data_and_drop
Revises: 0005_attempt_table
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_attempt_data_and_drop"
down_revision = "0005_attempt_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO attempt (word_id, kind, language_set, direction, part_of_speech,
                             was_correct, user_answer, correct_answer, practice_date, created_at)
        SELECT word_id, 'practice', language_set, direction, NULL,
               was_correct, user_answer, correct_answer, practice_date, created_at
        FROM practicerecord
    """)
    op.execute("""
        INSERT INTO attempt (word_id, kind, language_set, direction, part_of_speech,
                             was_correct, user_answer, correct_answer, practice_date, created_at)
        SELECT word_id, 'endings', NULL, NULL, part_of_speech,
               was_correct, user_answer, correct_answer, practice_date, created_at
        FROM endingspracticerecord
    """)
    op.drop_table("practicerecord")
    op.drop_table("endingspracticerecord")


def downgrade() -> None:
    op.create_table(
        "practicerecord",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("word_id", sa.Integer(), sa.ForeignKey("word.id"), nullable=False),
        sa.Column("language_set", sa.String(), nullable=False),
        sa.Column("direction", sa.String(), nullable=False),
        sa.Column("was_correct", sa.Boolean(), nullable=False),
        sa.Column("user_answer", sa.String(), nullable=True),
        sa.Column("correct_answer", sa.String(), nullable=True),
        sa.Column("practice_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "endingspracticerecord",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("word_id", sa.Integer(), sa.ForeignKey("word.id"), nullable=False),
        sa.Column("part_of_speech", sa.String(), nullable=False),
        sa.Column("was_correct", sa.Boolean(), nullable=False),
        sa.Column("user_answer", sa.String(), nullable=True),
        sa.Column("correct_answer", sa.String(), nullable=True),
        sa.Column("practice_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.execute("""
        INSERT INTO practicerecord (word_id, language_set, direction, was_correct,
                                    user_answer, correct_answer, practice_date, created_at)
        SELECT word_id, language_set, direction, was_correct,
               user_answer, correct_answer, practice_date, created_at
        FROM attempt WHERE kind = 'practice'
    """)
    op.execute("""
        INSERT INTO endingspracticerecord (word_id, part_of_speech, was_correct,
                                           user_answer, correct_answer, practice_date, created_at)
        SELECT word_id, part_of_speech, was_correct,
               user_answer, correct_answer, practice_date, created_at
        FROM attempt WHERE kind = 'endings'
    """)
    op.execute("DELETE FROM attempt")
```

- [ ] **Step 4: Run the migration tests (both acceptance tests now pass)**

Run: `.venv/bin/pytest tests/test_migrations.py -v`
Expected: PASS — including `test_upgrade_head_builds_attempt_and_drops_old_tables` and the data-copy test.

- [ ] **Step 5: Rewrite `calculate_stats`**

In `backend-app/app/utils.py`, replace the import on line 8:

```python
from app.models import Attempt, Word
```

and replace `calculate_stats` (lines 12-49):

```python
def calculate_stats(session: Session) -> StatsResponse:
    """Unified stats over the single Attempt table (M3)."""
    today = date.today()
    yesterday = today - timedelta(days=1)

    def aggregation(target_date: date) -> tuple[int, int]:
        rows = session.exec(
            select(Attempt).where(Attempt.practice_date == target_date)
        ).all()
        return sum(r.was_correct for r in rows), len(rows)

    today_correct, today_total = aggregation(today)
    yesterday_correct, yesterday_total = aggregation(yesterday)

    all_rows = session.exec(select(Attempt)).all()
    overall_total = len(all_rows)
    overall_correct = sum(r.was_correct for r in all_rows)

    word_count = session.scalar(select(func.count()).select_from(Word)) or 0

    def percent(correct: int, total: int) -> float:
        return (correct / total) * 100.0 if total else 0.0

    today_percent = percent(today_correct, today_total)
    yesterday_percent = percent(yesterday_correct, yesterday_total)
    overall_percent = percent(overall_correct, overall_total)
    return StatsResponse(
        today_percentage=round(today_percent, 1),
        trend=round(today_percent - yesterday_percent, 1),
        overall_percentage=round(overall_percent, 1),
        available_words=int(word_count),
    )
```

- [ ] **Step 6: Rewrite the history endpoint**

In `backend-app/app/api/stats.py`, replace the import on line 7:

```python
from app.models import Attempt, AttemptKind, Word
```

and replace the body of `get_history` (lines 34-80) with a single query (the `+1_000_000` id hack is no longer needed — `Attempt` ids are globally unique):

```python
    with Session(engine) as session:
        rows = session.exec(
            select(Attempt).order_by(Attempt.created_at.desc())
        ).all()
        records: list[HistoryRecord] = []
        for r in rows:
            word = session.get(Word, r.word_id)
            word_polish = word.polish if word else "?"
            word_translation = getattr(word, language_set, "?") if word else "?"
            if r.kind == AttemptKind.practice and r.direction is not None:
                section = r.direction.value
            else:
                section = "endings"
            records.append(HistoryRecord(
                id=r.id,
                word_polish=word_polish,
                word_translation=word_translation,
                section=section,
                was_correct=r.was_correct,
                created_at=r.created_at,
                user_answer=r.user_answer,
                correct_answer=r.correct_answer,
            ))

        total = len(records)
        page = records[offset:offset + limit]
        return HistoryResponse(records=page, total=total)
```

- [ ] **Step 7: Rewrite the practice write sites**

In `backend-app/app/api/practice.py`, change the model import block (lines 14-23) to import `Attempt`, `AttemptKind` instead of `PracticeRecord`:

```python
from app.models import (
    AppSetting,
    Attempt,
    AttemptKind,
    PracticeDirection,
    Word,
    WordLanguage,
    WordOption,
    UserSession,
    UserSessionWord,
)
```

Then replace each `PracticeRecord(...)` with the `Attempt` equivalent (`kind=AttemptKind.practice`):

Line 42 (`submit_practice`):
```python
        session.add(Attempt(kind=AttemptKind.practice, **payload.model_dump()))
```

Lines 105-114 (`validate_practice`):
```python
        session.add(
            Attempt(
                kind=AttemptKind.practice,
                word_id=word.id,
                language_set=payload.language_set,
                direction=payload.direction,
                was_correct=is_correct,
                user_answer=payload.answer,
                correct_answer=expected,
            )
        )
```

Lines 151-160 (`skip_practice`):
```python
        session.add(
            Attempt(
                kind=AttemptKind.practice,
                word_id=word.id,
                language_set=payload.language_set,
                direction=payload.direction,
                was_correct=False,
                user_answer="",
                correct_answer=expected,
            )
        )
```

Lines 206-215 (`validate_pronunciation`):
```python
        session.add(
            Attempt(
                kind=AttemptKind.practice,
                word_id=word.id,
                language_set=language_set,
                direction=PracticeDirection.pronunciation,
                was_correct=is_correct,
                user_answer=transcribed_text,
                correct_answer=word.polish,
            )
        )
```

Lines 330-339 (`validate_translation_choice`):
```python
        session.add(
            Attempt(
                kind=AttemptKind.practice,
                word_id=word.id,
                language_set=payload.language_set,
                direction=practice_direction,
                was_correct=is_correct,
                user_answer=payload.answer,
                correct_answer=correct_answer,
            )
        )
```

- [ ] **Step 8: Rewrite the endings write + stats**

In `backend-app/app/api/endings.py`, change the import of `EndingsPracticeRecord` to `Attempt, AttemptKind` (keep the other imported names). Replace the write block (lines 357-363):

```python
            session.add(Attempt(
                kind=AttemptKind.endings,
                word_id=payload.word_id,
                part_of_speech=word.part_of_speech,
                was_correct=was_correct,
                user_answer=payload.answer,
                correct_answer=payload.correct_answer,
            ))
```

Replace the three `select(EndingsPracticeRecord)...` queries in `_calculate_endings_stats` (lines 386-388, 394-398, 405) to filter `Attempt` by `kind`:

```python
    today_records = session.exec(
        select(Attempt).where(
            Attempt.kind == AttemptKind.endings,
            Attempt.practice_date == today,
        )
    ).all()
```
```python
    yesterday_records = session.exec(
        select(Attempt).where(
            Attempt.kind == AttemptKind.endings,
            Attempt.practice_date == yesterday,
        )
    ).all()
```
```python
    all_records = session.exec(
        select(Attempt).where(Attempt.kind == AttemptKind.endings)
    ).all()
```

- [ ] **Step 9: Rewrite the session cascade-delete and error-rate subquery**

In `backend-app/app/api/session.py`, replace the model-import block (lines 8-18):

```python
from app.models import (
    UserSession,
    UserSessionWord,
    Word,
    Attempt,
    AttemptKind,
    WordOption,
    WordDeclension,
    VerbConjugation,
    PracticeSentence,
)
```

Replace the two cascade loops — the block from the `# Remove practice records` comment through the end of the endings loop (lines 235-244) — with one loop:

```python
        # Remove all attempts for this word
        for record in session.exec(
            select(Attempt).where(Attempt.word_id == word_id)
        ).all():
            session.delete(record)
```

Replace the `stats_subquery` (lines 46-56) so it counts practice-kind attempts (preserving prior `PracticeRecord`-only semantics — see Design decision 6):

```python
    stats_subquery = (
        select(
            Attempt.word_id,
            func.count(Attempt.id).label("total_attempts"),
            func.sum(case((Attempt.was_correct == True, 1), else_=0)).label(
                "correct_attempts"
            ),
        )
        .where(Attempt.kind == AttemptKind.practice)
        .group_by(Attempt.word_id)
        .subquery()
    )
```

- [ ] **Step 10: Delete the old record models**

In `backend-app/app/models.py`, delete the `PracticeRecord` class (lines 158-167) and the `EndingsPracticeRecord` class (lines 170-178), including the `# ── Practice records ──` comment header.

- [ ] **Step 11: Grep for any stragglers**

Run: `grep -rn "PracticeRecord\|EndingsPracticeRecord" backend-app/ --include="*.py"`
Expected: no output (scope is the whole project, not just `app/` — a stray reference in `tests/` would otherwise `ImportError` at collection after the models are deleted). If anything remains, switch it to `Attempt` before proceeding.

- [ ] **Step 12: Write endpoint-level tests for the cutover**

Create `backend-app/tests/test_attempt_unification.py`:

```python
from sqlmodel import Session, select

from app.database import engine
from app.models import Attempt, AttemptKind, Word


def _make_word(polish="kot", pos="rzeczownik") -> int:
    with Session(engine) as s:
        w = Word(polish=polish, english="cat", ukrainian="кіт", part_of_speech=pos)
        s.add(w)
        s.commit()
        s.refresh(w)
        return w.id


def test_submit_writes_practice_attempt(client):
    wid = _make_word()
    resp = client.post("/api/practice/submit", json={
        "word_id": wid, "language_set": "english",
        "direction": "writing", "was_correct": True,
    })
    assert resp.status_code == 200
    with Session(engine) as s:
        rows = s.exec(select(Attempt)).all()
    assert len(rows) == 1
    assert rows[0].kind == AttemptKind.practice
    assert rows[0].direction.value == "writing"
    assert rows[0].language_set.value == "english"


def test_endings_validate_writes_endings_attempt(client):
    wid = _make_word()
    resp = client.post("/api/endings/validate", json={
        "word_id": wid, "answer": "kota", "correct_answer": "kotu",
    })
    assert resp.status_code == 200
    with Session(engine) as s:
        rows = s.exec(select(Attempt).where(Attempt.kind == AttemptKind.endings)).all()
    assert len(rows) == 1
    assert rows[0].part_of_speech is not None
    assert rows[0].language_set is None


def test_history_unifies_both_kinds(client):
    wid = _make_word()
    client.post("/api/practice/submit", json={
        "word_id": wid, "language_set": "english",
        "direction": "writing", "was_correct": True,
    })
    client.post("/api/endings/validate", json={
        "word_id": wid, "answer": "x", "correct_answer": "y",
    })
    resp = client.get("/api/stats/history")
    assert resp.status_code == 200
    sections = {r["section"] for r in resp.json()["records"]}
    assert "writing" in sections and "endings" in sections
```

> Verify the two endpoint paths and the endings request body against the live routers before running (prefixes are mounted under `/api` in `main.py`; the endings validate schema is `EndingsValidationRequest`). Adjust the JSON keys if the schema differs.

- [ ] **Step 13: Run the full suite**

Run: `.venv/bin/pytest -v`
Expected: PASS — all tests green, including `test_migrations.py` and `test_attempt_unification.py`.

- [ ] **Step 14: Confirm the app imports**

Run: `POLINGO_DATABASE_URL="sqlite://" .venv/bin/python -c "import main; print('import ok')"`
Expected: prints `import ok`.

- [ ] **Step 15: Commit**

```bash
git add backend-app/app backend-app/migrations/versions/0006_attempt_data_and_drop.py backend-app/tests/test_attempt_unification.py backend-app/tests/test_migrations.py
git commit -m "feat: cut over to unified Attempt table; drop old record tables (M3)"
```

---

### Task 7: Update documentation

**Files:**
- Modify: `.claude/CONTEXT.md` (Attempt/Form/virility tags)
- Modify: `.claude/BACKLOG.md` (statuses + changelog + plan series)
- Modify: `README.md` (migrations note)

- [ ] **Step 1: Update the glossary**

In `.claude/CONTEXT.md`:
- In the **Form** entry, change the virility note from *[planned]* to *[live]* and reference the 5-gender model + `is_virile`.
- In the **Attempt** entry, change *[planned]* to *[live]* and replace "Today this does not exist… two disjoint tables…" with: "Backed by the single `Attempt` table (Plan 2); `kind` discriminates practice vs endings. Stats and history read this one table."
- In the **Topic** entry, note that the `aspect` field now exists on `Word` (nullable) though aspect exercises/data are still planned.

- [ ] **Step 2: Update the backlog**

In `.claude/BACKLOG.md`:
- Plan series row 2 → `✅ complete` (cite branch).
- B1 → ✅ (Plan 2: 5-gender model + oni/one split). Add a note that masculine-personal/animate re-tagging is a documented follow-up.
- B3 → ✅ (Alembic adopted, Plan 2 Task 1).
- M3 → ✅ structural (Attempt unification).
- M4 → flip the "aspect field" half to ✅ (column added); data/exercises remain 🔜 Plan 4.
- Add a dated Changelog entry summarising Plan 2 with per-task commit refs.

- [ ] **Step 3: Document migrations in the README**

In `README.md`, in the backend section, add:

```markdown
### Database migrations

Schema is managed by Alembic. `init_db()` runs `alembic upgrade head` on startup;
existing pre-Alembic databases are stamped at the baseline first, so data is preserved.
To create a new migration:

```bash
cd backend-app
.venv/bin/alembic revision -m "describe change"      # hand-written
.venv/bin/alembic revision --autogenerate -m "..."   # diff models vs DB
```
```

- [ ] **Step 4: Commit**

```bash
git add .claude/CONTEXT.md .claude/BACKLOG.md README.md
git commit -m "docs: mark Attempt/virility live; document Alembic migrations (Plan 2)"
```

---

## Self-review

**Spec coverage (against Plan 2 scope + the locked decisions):**
- Alembic adoption (B3 structural) → Task 1. ✓
- Virility 5-gender model + `is_virile` (B1) → Task 2; pronoun `oni`/`one` split (B1) → Task 3. ✓
- Nullable `aspect` on `Word` (M4/M5 groundwork) → Task 4. ✓
- Unified `Attempt` table (M3) → Task 5 (table) + Task 6 (data copy, cutover, drop). ✓
- Lossless data migration with preservation test → Task 6 Step 1. ✓
- Drop old tables in the copy migration (decision 5) → Task 6 migration `0006`. ✓
- Stat-semantics preserved (decision 6) → Task 6 Step 9. ✓
- Docs (CONTEXT/BACKLOG/README) → Task 7. ✓

**Placeholder scan:** No TBD/TODO/"add error handling". Every code, migration, and test step shows full content. The one judgement call (autogenerated baseline body in Task 1) is intentional — autogenerate is the correct, less error-prone way to capture 11 existing tables, and the step verifies the output. ✓

**Type/name consistency:** `is_virile`, `GrammaticalGender` 5 members, `Pronoun.oni`/`.one`, `Aspect.{dokonany,niedokonany}`, `Word.aspect`, `AttemptKind.{practice,endings}`, and `Attempt`'s field set are used identically across Tasks 2–6 and all tests. Migration revision ids form a single chain `0001_baseline → 0002 → 0003 → 0004 → 0005 → 0006` with matching `down_revision`s. `run_migrations`/`_alembic_config` defined in Task 1 are reused by `test_migrations.py`. ✓

**Review fixes folded in (3-reviewer pass, 2026-06-18):** env.py resolves the DB URL at run time not import time; `run_migrations` inspects an engine built from the resolved URL; the migration-test helper uses absolute paths; the acceptance test is `xfail` (strict) until Task 6 so every commit's suite is green; migration `0006` downgrade is corrected; `session.py` gets an explicit import block; the straggler grep covers the whole project; the three `Word(...)` edits use content anchors. Linguistics: `is_animate_masculine()` accompanies `is_virile()` so singular-accusative animacy is never decided by virility; migration `0003` duplicates present/future rows as `one` (only past tense is left for regeneration); the conjugation prompt states oni/one are identical outside past tense.

**Known limitation (recorded, not a gap):** legacy `męski` rows collapse to `męskorzeczowy` (decision 2) — wrong accusative singular for animate masculines and wrong accusative-plural/virile agreement for personal masculines until re-tagging; and `one` *past-tense* forms are not fabricated (decision 3). Both are documented in the migrations and the backlog, with regeneration/re-tagging assigned to a later plan.
