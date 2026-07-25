# Adjective Grading (Stopniowanie przymiotników) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new `/grading` practice section teaching Polish adjective grading (proste / nieregularne / opisowe) with choose + write modes, mirroring the existing Endings section.

**Architecture:** New `AdjectiveGrading` table (one row per adjective, nominative base forms only) seeded with hardcoded data. New `app/api/grading.py` router mirrors `app/api/endings.py`: config / question / validate / stats. Multiple-choice distractors are LLM-generated once and cached on the row. Frontend adds an inline view in `App.jsx` cloned from the Endings view; the page-extraction refactor is deferred to backlog.

**Tech Stack:** FastAPI, SQLModel, SQLite, Alembic, pytest (backend); React + Vite, Vitest (frontend).

**Key facts about this codebase (read before starting):**
- API is mounted under `/api` (`main.py:148`), so endpoints are `/api/grading/*`. The frontend `apiFetch` already prepends the base, and clients pass paths like `/grading/config`.
- `AttemptKind` is a `str` Enum stored in a `String` column — adding a value is a **Python-only change, no migration**.
- Tests use an in-memory SQLite built from model metadata (`conftest.py` `fresh_db`), and `fake_llm` (autouse) monkeypatches every `app.llm.*` network call. Any new LLM function MUST be patched there or tests hit the network.
- Migrations live in `migrations/versions/`; head is `0006_attempt_data_and_drop`.
- Nominative base forms only — comparatives do NOT get case/gender declension in this feature.

---

## File Structure

- Modify `backend-app/app/models.py` — add `GradingType` enum, `AttemptKind.grading`, `AdjectiveGrading` table.
- Create `backend-app/migrations/versions/0007_adjective_grading.py` — create `adjectivegrading` table.
- Modify `backend-app/app/grammar.py` — `ADJECTIVE_GRADING_RULES` + `grading_type` param on `get_grammar_reference`.
- Modify `backend-app/app/llm.py` — `generate_grading_distractors_via_llm`.
- Modify `backend-app/tests/conftest.py` — patch the new LLM function.
- Modify `backend-app/app/seed.py` — `GRADING_DATA` + `seed_grading`.
- Modify `backend-app/app/database.py` — call `seed_grading` in `init_db`.
- Modify `backend-app/app/schemas.py` — grading schemas.
- Create `backend-app/app/api/grading.py` — router.
- Modify `backend-app/app/api/__init__.py` — register router.
- Create `backend-app/tests/contract/test_grading.py` — contract tests.
- Create `frontend-app/src/api/grading.js` — API client.
- Modify `frontend-app/src/api/index.js` — re-export grading.
- Create `frontend-app/src/api/grading.test.js` — client tests.
- Modify `frontend-app/src/App.jsx` — nav card, route, state, handlers, view.

---

## Task 1: Models — enum, AttemptKind, AdjectiveGrading table

**Files:**
- Modify: `backend-app/app/models.py` (enums near line 83; `AttemptKind` line 192; add table near `WordDeclension` line 129)
- Test: `backend-app/tests/test_grading_model.py` (create)

- [ ] **Step 1: Write the failing test**

Create `backend-app/tests/test_grading_model.py`:

```python
from sqlmodel import Session, select

from app.database import engine
from app.models import AdjectiveGrading, AttemptKind, GradingType, Word, PartOfSpeech


def test_adjective_grading_roundtrip():
    with Session(engine) as session:
        w = Word(polish="dobry", english="good", ukrainian="добрий",
                 part_of_speech=PartOfSpeech.przymiotnik)
        session.add(w)
        session.commit()
        session.refresh(w)
        session.add(AdjectiveGrading(
            word_id=w.id, grading_type=GradingType.nieregularne,
            comparative="lepszy", superlative="najlepszy",
        ))
        session.commit()
        row = session.exec(select(AdjectiveGrading)).one()
        assert row.grading_type == GradingType.nieregularne
        assert row.comparative == "lepszy"
        assert row.superlative == "najlepszy"
        assert row.comparative_distractors is None


def test_attemptkind_has_grading():
    assert AttemptKind.grading.value == "grading"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend-app && python -m pytest tests/test_grading_model.py -v`
Expected: FAIL with `ImportError: cannot import name 'AdjectiveGrading'` (or `GradingType`).

- [ ] **Step 3: Add the enum, AttemptKind value, and table**

In `backend-app/app/models.py`, after the `VerbTense` enum (ends line 86), add:

```python
class GradingType(str, Enum):
    proste = "proste"              # regular synthetic: ładny → ładniejszy
    nieregularne = "nieregularne"  # irregular: dobry → lepszy
    opisowe = "opisowe"            # descriptive: znany → bardziej znany
```

In `AttemptKind` (line 192), add the member:

```python
class AttemptKind(str, Enum):
    practice = "practice"   # translation / writing / pronunciation
    endings = "endings"     # grammar endings practice
    grading = "grading"     # adjective grading (stopniowanie)
```

After the `WordDeclension` class (ends line 143), add:

```python
class AdjectiveGrading(SQLModel, table=True):
    """Nominative-base comparative/superlative forms for one adjective.
    Distractor columns hold a JSON list of cached wrong options (lazy-filled)."""
    __table_args__ = (UniqueConstraint("word_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    word_id: int = Field(foreign_key="word.id", index=True)
    grading_type: GradingType
    comparative: str
    superlative: str
    comparative_distractors: Optional[str] = Field(default=None)
    superlative_distractors: Optional[str] = Field(default=None)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend-app && python -m pytest tests/test_grading_model.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add backend-app/app/models.py backend-app/tests/test_grading_model.py
git commit -m "feat(models): AdjectiveGrading table + GradingType + AttemptKind.grading"
```

---

## Task 2: Alembic migration for adjectivegrading table

**Files:**
- Create: `backend-app/migrations/versions/0007_adjective_grading.py`
- Test: reuse existing `backend-app/tests/test_migrations.py` (runs upgrade to head against a file DB)

- [ ] **Step 1: Write the migration**

Create `backend-app/migrations/versions/0007_adjective_grading.py`:

```python
"""create adjectivegrading table

Revision ID: 0007_adjective_grading
Revises: 0006_attempt_data_and_drop
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_adjective_grading"
down_revision = "0006_attempt_data_and_drop"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "adjectivegrading",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("word_id", sa.Integer(), sa.ForeignKey("word.id"), nullable=False),
        sa.Column("grading_type", sa.String(), nullable=False),
        sa.Column("comparative", sa.String(), nullable=False),
        sa.Column("superlative", sa.String(), nullable=False),
        sa.Column("comparative_distractors", sa.String(), nullable=True),
        sa.Column("superlative_distractors", sa.String(), nullable=True),
        sa.UniqueConstraint("word_id", name="uq_adjectivegrading_word_id"),
    )
    op.create_index("ix_adjectivegrading_word_id", "adjectivegrading", ["word_id"])


def downgrade() -> None:
    op.drop_index("ix_adjectivegrading_word_id", table_name="adjectivegrading")
    op.drop_table("adjectivegrading")
```

- [ ] **Step 2: Run the migration test to verify head upgrades cleanly**

Run: `cd backend-app && python -m pytest tests/test_migrations.py -v`
Expected: PASS (the suite upgrades a fresh file DB to head; the new revision must apply without error).

- [ ] **Step 3: Manually verify the revision chain**

Run: `cd backend-app && python -m alembic heads`
Expected: single head `0007_adjective_grading (head)`.

- [ ] **Step 4: Commit**

```bash
git add backend-app/migrations/versions/0007_adjective_grading.py
git commit -m "feat(db): migration 0007 create adjectivegrading table"
```

---

## Task 3: Grammar reference for grading types

**Files:**
- Modify: `backend-app/app/grammar.py` (add block near `ADJECTIVE_ENDINGS`; extend `get_grammar_reference` at line 197)
- Test: `backend-app/tests/test_grammar_reference.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `backend-app/tests/test_grammar_reference.py`:

```python
def test_grammar_reference_grading():
    from app.grammar import get_grammar_reference
    ref = get_grammar_reference("przymiotnik", grading_type="nieregularne")
    assert "grading_rules" in ref
    assert "dobry" in str(ref["grading_rules"])


def test_grammar_reference_grading_opisowe():
    from app.grammar import get_grammar_reference
    ref = get_grammar_reference("przymiotnik", grading_type="opisowe")
    assert "grading_rules" in ref
    assert "bardziej" in str(ref["grading_rules"]).lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend-app && python -m pytest tests/test_grammar_reference.py -k grading -v`
Expected: FAIL with `TypeError: get_grammar_reference() got an unexpected keyword argument 'grading_type'`.

- [ ] **Step 3: Add the rules block and extend the function**

In `backend-app/app/grammar.py`, after the `ADJECTIVE_ENDINGS` dict (ends line 81), add:

```python
# ── Stopniowanie przymiotników (Adjective grading) ──────────

ADJECTIVE_GRADING_RULES = {
    "proste": {
        "rule": "Stopniowanie proste (syntetyczne): stopień wyższy = temat + -szy/-ejszy; "
                "stopień najwyższy = naj- + stopień wyższy.",
        "examples": "ładny → ładniejszy → najładniejszy; tani → tańszy → najtańszy; "
                    "młody → młodszy → najmłodszy",
    },
    "nieregularne": {
        "rule": "Stopniowanie nieregularne: formy trzeba zapamiętać — nie tworzy się ich regularnie.",
        "examples": "dobry → lepszy → najlepszy; zły → gorszy → najgorszy; "
                    "duży → większy → największy; mały → mniejszy → najmniejszy",
    },
    "opisowe": {
        "rule": "Stopniowanie opisowe (analityczne): stopień wyższy = bardziej + przymiotnik; "
                "stopień najwyższy = najbardziej + przymiotnik.",
        "examples": "znany → bardziej znany → najbardziej znany; "
                    "chory → bardziej chory → najbardziej chory",
    },
}
```

Change the `get_grammar_reference` signature (line 197) and add a grading branch. Replace:

```python
def get_grammar_reference(part_of_speech: str, case: str = None, tense: str = None) -> dict:
    """Get the relevant grammar reference for a practice question."""
    result = {}

    if part_of_speech == "rzeczownik":
```

with:

```python
def get_grammar_reference(
    part_of_speech: str, case: str = None, tense: str = None, grading_type: str = None
) -> dict:
    """Get the relevant grammar reference for a practice question."""
    result = {}

    if grading_type is not None:
        result["grading_rules"] = ADJECTIVE_GRADING_RULES.get(grading_type, {})
        return result

    if part_of_speech == "rzeczownik":
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend-app && python -m pytest tests/test_grammar_reference.py -k grading -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add backend-app/app/grammar.py backend-app/tests/test_grammar_reference.py
git commit -m "feat(grammar): ADJECTIVE_GRADING_RULES + grading_type reference lookup"
```

---

## Task 4: LLM distractor generator + test fake

**Files:**
- Modify: `backend-app/app/llm.py` (add function near `generate_declensions_via_llm` line 182)
- Modify: `backend-app/tests/conftest.py` (patch in `fake_llm`, after line 50)
- Test: `backend-app/tests/test_grading_llm_fake.py` (create)

- [ ] **Step 1: Write the failing test**

Create `backend-app/tests/test_grading_llm_fake.py`:

```python
def test_fake_grading_distractors_returns_three():
    from app import llm
    out = llm.generate_grading_distractors_via_llm(
        positive="dobry", correct="lepszy", degree="comparative", grading_type="nieregularne"
    )
    assert isinstance(out, list)
    assert len(out) == 3
    assert "lepszy" not in out
```

(The autouse `fake_llm` fixture must patch the function; this test verifies the fake is wired.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend-app && python -m pytest tests/test_grading_llm_fake.py -v`
Expected: FAIL with `AttributeError: module 'app.llm' has no attribute 'generate_grading_distractors_via_llm'`.

- [ ] **Step 3: Add the real LLM function**

In `backend-app/app/llm.py`, after `generate_declensions_via_llm` (ends line 222), add:

```python
def generate_grading_distractors_via_llm(
    positive: str, correct: str, degree: str, grading_type: str
) -> list[str]:
    """Generate 3 plausible-but-wrong Polish grading forms for a choose question.
    `degree` is 'comparative' or 'superlative'. Returns a list of 3 distinct
    strings, none equal to `correct`."""
    client = get_openai_client()
    prompt = (
        "You are a Polish language expert building a multiple-choice grammar quiz. "
        "Given a base adjective, the correct graded form, the degree, and the grading "
        "type, produce exactly 3 plausible but INCORRECT alternative forms a learner "
        "might confuse it with. Never repeat the correct answer. "
        "Return JSON with key 'distractors' — an array of exactly 3 strings."
    )
    response = client.responses.create(
        model=config.text_model(),
        instructions=prompt,
        input=(
            f"Respond in JSON.\nBase adjective: {positive}\nCorrect {degree}: {correct}\n"
            f"Grading type: {grading_type}"
        ),
        text={"format": {"type": "json_object"}},
    )
    content = response.output_text or "{}"
    payload: Dict[str, Any] = json.loads(content)
    distractors = [d for d in payload.get("distractors", []) if d and d != correct]
    return distractors[:3]
```

- [ ] **Step 4: Patch the fake in conftest**

In `backend-app/tests/conftest.py`, inside the `fake_llm` fixture (after the `generate_practice_sentences_via_llm` patch, line 50), add:

```python
    monkeypatch.setattr(
        llm, "generate_grading_distractors_via_llm",
        lambda positive, correct, degree, grading_type: [
            f"{correct}x", f"{correct}y", f"{positive}sz",
        ],
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend-app && python -m pytest tests/test_grading_llm_fake.py -v`
Expected: PASS (1 passed).

- [ ] **Step 6: Commit**

```bash
git add backend-app/app/llm.py backend-app/tests/conftest.py backend-app/tests/test_grading_llm_fake.py
git commit -m "feat(llm): grading distractor generator + test fake"
```

---

## Task 5: Seed data for grading adjectives

**Files:**
- Modify: `backend-app/app/seed.py` (add `GRADING_DATA` + `seed_grading`)
- Modify: `backend-app/app/database.py` (call `seed_grading` in `init_db`, near line 73)
- Test: `backend-app/tests/test_grading_seed.py` (create)

- [ ] **Step 1: Write the failing test**

Create `backend-app/tests/test_grading_seed.py`:

```python
from sqlmodel import Session, select

from app.database import engine
from app.models import AdjectiveGrading, GradingType, Word, PartOfSpeech
from app.seed import seed_grading


def test_seed_grading_creates_rows_and_words():
    with Session(engine) as session:
        seed_grading(session)
        rows = session.exec(select(AdjectiveGrading)).all()
        assert len(rows) >= 20
        types = {r.grading_type for r in rows}
        assert types == {GradingType.proste, GradingType.nieregularne, GradingType.opisowe}
        # every grading row points at a przymiotnik Word
        for r in rows:
            w = session.get(Word, r.word_id)
            assert w is not None
            assert w.part_of_speech == PartOfSpeech.przymiotnik


def test_seed_grading_is_idempotent():
    with Session(engine) as session:
        seed_grading(session)
        seed_grading(session)
        rows = session.exec(select(AdjectiveGrading)).all()
        words = session.exec(
            select(Word).where(Word.polish == "dobry")
        ).all()
        assert len(words) == 1  # not duplicated
        # no duplicate grading rows per word
        word_ids = [r.word_id for r in rows]
        assert len(word_ids) == len(set(word_ids))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend-app && python -m pytest tests/test_grading_seed.py -v`
Expected: FAIL with `ImportError: cannot import name 'seed_grading'`.

- [ ] **Step 3: Add GRADING_DATA and seed_grading**

In `backend-app/app/seed.py`, update the import line and append the data + function. Change the top import:

```python
from sqlmodel import Session, select

from app.models import AdjectiveGrading, GradingType, PartOfSpeech, Word
```

At the end of the file add:

```python
# polish, english, ukrainian, type, comparative, superlative
GRADING_DATA = [
    # nieregularne
    ("dobry", "good", "добрий", "nieregularne", "lepszy", "najlepszy"),
    ("zły", "bad", "поганий", "nieregularne", "gorszy", "najgorszy"),
    ("duży", "big", "великий", "nieregularne", "większy", "największy"),
    ("mały", "small", "малий", "nieregularne", "mniejszy", "najmniejszy"),
    ("wysoki", "tall", "високий", "nieregularne", "wyższy", "najwyższy"),
    ("niski", "low", "низький", "nieregularne", "niższy", "najniższy"),
    ("lekki", "light", "легкий", "nieregularne", "lżejszy", "najlżejszy"),
    ("ciężki", "heavy", "важкий", "nieregularne", "cięższy", "najcięższy"),
    ("daleki", "far", "далекий", "nieregularne", "dalszy", "najdalszy"),
    ("bliski", "close", "близький", "nieregularne", "bliższy", "najbliższy"),
    # proste
    ("ładny", "pretty", "гарний", "proste", "ładniejszy", "najładniejszy"),
    ("tani", "cheap", "дешевий", "proste", "tańszy", "najtańszy"),
    ("ciekawy", "interesting", "цікавий", "proste", "ciekawszy", "najciekawszy"),
    ("zimny", "cold", "холодний", "proste", "zimniejszy", "najzimniejszy"),
    ("ciepły", "warm", "теплий", "proste", "cieplejszy", "najcieplejszy"),
    ("młody", "young", "молодий", "proste", "młodszy", "najmłodszy"),
    ("stary", "old", "старий", "proste", "starszy", "najstarszy"),
    ("nowy", "new", "новий", "proste", "nowszy", "najnowszy"),
    ("szybki", "fast", "швидкий", "proste", "szybszy", "najszybszy"),
    ("silny", "strong", "сильний", "proste", "silniejszy", "najsilniejszy"),
    ("słaby", "weak", "слабкий", "proste", "słabszy", "najsłabszy"),
    ("mądry", "wise", "мудрий", "proste", "mądrzejszy", "najmądrzejszy"),
    # opisowe
    ("znany", "known", "відомий", "opisowe", "bardziej znany", "najbardziej znany"),
    ("chory", "sick", "хворий", "opisowe", "bardziej chory", "najbardziej chory"),
    ("zmęczony", "tired", "втомлений", "opisowe", "bardziej zmęczony", "najbardziej zmęczony"),
    ("zajęty", "busy", "зайнятий", "opisowe", "bardziej zajęty", "najbardziej zajęty"),
    ("popularny", "popular", "популярний", "opisowe", "bardziej popularny", "najbardziej popularny"),
    ("kolorowy", "colorful", "барвистий", "opisowe", "bardziej kolorowy", "najbardziej kolorowy"),
]


def seed_grading(session: Session) -> None:
    """Idempotently create adjective Words + AdjectiveGrading rows."""
    for polish, english, ukrainian, gtype, comp, sup in GRADING_DATA:
        word = session.exec(select(Word).where(Word.polish == polish)).first()
        if word is None:
            word = Word(
                polish=polish, english=english, ukrainian=ukrainian,
                part_of_speech=PartOfSpeech.przymiotnik,
            )
            session.add(word)
            session.commit()
            session.refresh(word)
        exists = session.exec(
            select(AdjectiveGrading).where(AdjectiveGrading.word_id == word.id)
        ).first()
        if exists is None:
            session.add(AdjectiveGrading(
                word_id=word.id, grading_type=GradingType(gtype),
                comparative=comp, superlative=sup,
            ))
    session.commit()
```

- [ ] **Step 4: Wire seed_grading into init_db**

In `backend-app/app/database.py`, update the seed import (line 12) and call it. Change:

```python
from app.seed import seed_words
```

to:

```python
from app.seed import seed_grading, seed_words
```

In `init_db` (after the `seed_words(session)` block, around line 73), add:

```python
        seed_grading(session)
```

Place it immediately after the `if not has_words: seed_words(session)` block so it runs every startup (it is idempotent).

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend-app && python -m pytest tests/test_grading_seed.py -v`
Expected: PASS (2 passed).

- [ ] **Step 6: Commit**

```bash
git add backend-app/app/seed.py backend-app/app/database.py backend-app/tests/test_grading_seed.py
git commit -m "feat(seed): adjective grading seed data + idempotent seed_grading"
```

---

## Task 6: Grading schemas

**Files:**
- Modify: `backend-app/app/schemas.py` (after `EndingsConfigResponse`, line 224)
- Test: covered by Task 8 contract tests (no standalone test — schemas are validated via the endpoints)

- [ ] **Step 1: Add the schemas**

In `backend-app/app/schemas.py`, after `EndingsConfigResponse` (ends line 224), add:

```python
class GradingConfigResponse(SQLModel):
    grading_types: list[str]
    counts: dict[str, int]


class GradingQuestion(SQLModel):
    word_id: int
    positive: str
    english: str
    ukrainian: str
    grading_type: str
    degree: str            # "comparative" | "superlative"
    correct_answer: str
    options: list[str]     # 4 options (choose mode)
    grammar_reference: dict[str, Any] = {}


class GradingValidationRequest(SQLModel):
    word_id: int
    answer: str
    correct_answer: str


class GradingStatsResponse(SQLModel):
    today_percentage: float
    trend: float
    overall_percentage: float
    available_words: int


class GradingValidationResponse(SQLModel):
    was_correct: bool
    correct_answer: str
    stats: GradingStatsResponse
```

- [ ] **Step 2: Verify it imports**

Run: `cd backend-app && python -c "from app.schemas import GradingQuestion, GradingConfigResponse, GradingValidationRequest, GradingValidationResponse, GradingStatsResponse; print('ok')"`
Expected: prints `ok`.

- [ ] **Step 3: Commit**

```bash
git add backend-app/app/schemas.py
git commit -m "feat(schemas): grading config/question/validate/stats schemas"
```

---

## Task 7: Grading router

**Files:**
- Create: `backend-app/app/api/grading.py`
- Modify: `backend-app/app/api/__init__.py` (register router)
- Test: Task 8

- [ ] **Step 1: Write the router**

Create `backend-app/app/api/grading.py`:

```python
import json
import random
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, func, select

from app.database import engine
from app.grammar import get_grammar_reference
from app.llm import generate_grading_distractors_via_llm
from app.models import (
    AdjectiveGrading,
    Attempt,
    AttemptKind,
    GradingType,
    PartOfSpeech,
    Word,
)
from app.schemas import (
    GradingConfigResponse,
    GradingQuestion,
    GradingStatsResponse,
    GradingValidationRequest,
    GradingValidationResponse,
)

router = APIRouter(prefix="/grading", tags=["grading"])


@router.get("/config", response_model=GradingConfigResponse)
def get_grading_config() -> GradingConfigResponse:
    with Session(engine) as session:
        counts: dict[str, int] = {}
        for gt in GradingType:
            n = session.exec(
                select(func.count(AdjectiveGrading.id)).where(
                    AdjectiveGrading.grading_type == gt
                )
            ).one()
            counts[gt.value] = n
    return GradingConfigResponse(
        grading_types=[gt.value for gt in GradingType],
        counts=counts,
    )


def _distractors_for(
    session: Session, row: AdjectiveGrading, degree: str, correct: str
) -> list[str]:
    """Return 3 cached distractors, generating + persisting them on first use."""
    column = "comparative_distractors" if degree == "comparative" else "superlative_distractors"
    cached = getattr(row, column)
    if cached:
        return json.loads(cached)
    word = session.get(Word, row.word_id)
    generated = generate_grading_distractors_via_llm(
        positive=word.polish, correct=correct,
        degree=degree, grading_type=row.grading_type.value,
    )
    setattr(row, column, json.dumps(generated))
    session.add(row)
    session.commit()
    return generated


@router.get("/question", response_model=GradingQuestion)
def get_grading_question(
    grading_types: str | None = None,
    exclude_word_id: int | None = None,
) -> GradingQuestion:
    requested = [t.strip() for t in (grading_types or "").split(",") if t.strip()]
    with Session(engine) as session:
        stmt = select(AdjectiveGrading)
        if requested:
            stmt = stmt.where(AdjectiveGrading.grading_type.in_(requested))
        rows = session.exec(stmt).all()
        if not rows:
            raise HTTPException(
                status_code=404,
                detail="No adjectives available for grading practice.",
            )
        candidates = [r for r in rows if r.word_id != exclude_word_id] or rows
        row = random.choice(candidates)
        word = session.get(Word, row.word_id)

        degree = random.choice(["comparative", "superlative"])
        correct = row.comparative if degree == "comparative" else row.superlative

        distractors = _distractors_for(session, row, degree, correct)
        options = [correct] + [d for d in distractors if d != correct]
        random.shuffle(options)

        grammar = get_grammar_reference(
            "przymiotnik", grading_type=row.grading_type.value
        )
        return GradingQuestion(
            word_id=word.id,
            positive=word.polish,
            english=word.english,
            ukrainian=word.ukrainian,
            grading_type=row.grading_type.value,
            degree=degree,
            correct_answer=correct,
            options=options,
            grammar_reference=grammar,
        )


@router.post("/validate", response_model=GradingValidationResponse)
def validate_grading(payload: GradingValidationRequest) -> GradingValidationResponse:
    answer = payload.answer.strip().lower()
    correct = payload.correct_answer.strip().lower()
    was_correct = answer == correct
    with Session(engine) as session:
        word = session.get(Word, payload.word_id)
        if word:
            session.add(Attempt(
                kind=AttemptKind.grading,
                word_id=payload.word_id,
                part_of_speech=word.part_of_speech,
                was_correct=was_correct,
                user_answer=payload.answer,
                correct_answer=payload.correct_answer,
            ))
            session.commit()
        stats = _calculate_grading_stats(session)
    return GradingValidationResponse(
        was_correct=was_correct,
        correct_answer=payload.correct_answer,
        stats=stats,
    )


@router.get("/stats", response_model=GradingStatsResponse)
def get_grading_stats() -> GradingStatsResponse:
    with Session(engine) as session:
        return _calculate_grading_stats(session)


def _calculate_grading_stats(session: Session) -> GradingStatsResponse:
    today = date.today()
    yesterday = today - timedelta(days=1)

    def pct(records):
        total = len(records)
        correct = sum(1 for r in records if r.was_correct)
        return (correct / total * 100) if total > 0 else 0.0

    today_records = session.exec(
        select(Attempt).where(
            Attempt.kind == AttemptKind.grading,
            Attempt.practice_date == today,
        )
    ).all()
    yesterday_records = session.exec(
        select(Attempt).where(
            Attempt.kind == AttemptKind.grading,
            Attempt.practice_date == yesterday,
        )
    ).all()
    all_records = session.exec(
        select(Attempt).where(Attempt.kind == AttemptKind.grading)
    ).all()

    today_pct = pct(today_records)
    trend = today_pct - pct(yesterday_records)

    available_words = session.exec(
        select(func.count(AdjectiveGrading.id))
    ).one()

    return GradingStatsResponse(
        today_percentage=round(today_pct, 1),
        trend=round(trend, 1),
        overall_percentage=round(pct(all_records), 1),
        available_words=available_words,
    )
```

- [ ] **Step 2: Register the router**

In `backend-app/app/api/__init__.py`, add the import (after the `endings` import) and include it (after `router.include_router(endings_router)`):

```python
from app.api.grading import router as grading_router
```

```python
router.include_router(grading_router)
```

- [ ] **Step 3: Verify the app boots**

Run: `cd backend-app && python -c "from main import app; print([r.path for r in app.routes if 'grading' in r.path])"`
Expected: prints a list containing `/api/grading/config`, `/api/grading/question`, `/api/grading/validate`, `/api/grading/stats`.

- [ ] **Step 4: Commit**

```bash
git add backend-app/app/api/grading.py backend-app/app/api/__init__.py
git commit -m "feat(api): /grading router (config/question/validate/stats)"
```

---

## Task 8: Backend contract tests

**Files:**
- Create: `backend-app/tests/contract/test_grading.py`

- [ ] **Step 1: Write the tests**

Create `backend-app/tests/contract/test_grading.py`:

```python
from sqlmodel import Session

from app.database import engine
from app.models import AdjectiveGrading, GradingType, PartOfSpeech, Word


def _seed_one(gtype=GradingType.nieregularne, polish="dobry", comp="lepszy", sup="najlepszy"):
    with Session(engine) as session:
        w = Word(polish=polish, english="good", ukrainian="добрий",
                 part_of_speech=PartOfSpeech.przymiotnik)
        session.add(w)
        session.commit()
        session.refresh(w)
        session.add(AdjectiveGrading(
            word_id=w.id, grading_type=gtype, comparative=comp, superlative=sup,
        ))
        session.commit()
        return w.id


def test_config_reports_types_and_counts(client):
    _seed_one()
    r = client.get("/api/grading/config")
    assert r.status_code == 200
    body = r.json()
    assert set(body["grading_types"]) == {"proste", "nieregularne", "opisowe"}
    assert body["counts"]["nieregularne"] == 1


def test_question_returns_correct_in_options_with_grammar(client):
    _seed_one()
    r = client.get("/api/grading/question?grading_types=nieregularne")
    assert r.status_code == 200
    q = r.json()
    assert q["degree"] in ("comparative", "superlative")
    assert q["correct_answer"] in q["options"]
    assert len(q["options"]) == 4
    assert "grading_rules" in q["grammar_reference"]


def test_question_404_when_empty(client):
    r = client.get("/api/grading/question?grading_types=proste")
    assert r.status_code == 404


def test_distractors_cached_after_first_question(client):
    word_id = _seed_one()
    # Force many draws so both degrees get exercised and cached.
    for _ in range(10):
        client.get("/api/grading/question?grading_types=nieregularne")
    with Session(engine) as session:
        row = session.get(AdjectiveGrading, 1)
        assert row.comparative_distractors or row.superlative_distractors


def test_validate_records_attempt_and_returns_stats(client):
    _seed_one()
    r = client.post("/api/grading/validate", json={
        "word_id": 1, "answer": "lepszy", "correct_answer": "lepszy",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["was_correct"] is True
    assert body["stats"]["overall_percentage"] == 100.0


def test_validate_wrong_answer(client):
    _seed_one()
    r = client.post("/api/grading/validate", json={
        "word_id": 1, "answer": "gorszy", "correct_answer": "lepszy",
    })
    assert r.json()["was_correct"] is False
```

- [ ] **Step 2: Run the tests**

Run: `cd backend-app && python -m pytest tests/contract/test_grading.py -v`
Expected: PASS (6 passed).

- [ ] **Step 3: Run the full backend suite (no regressions)**

Run: `cd backend-app && python -m pytest -q`
Expected: all pass (previous suite + new grading tests).

- [ ] **Step 4: Commit**

```bash
git add backend-app/tests/contract/test_grading.py
git commit -m "test(grading): contract tests for /grading endpoints"
```

---

## Task 9: Frontend API client

**Files:**
- Create: `frontend-app/src/api/grading.js`
- Modify: `frontend-app/src/api/index.js`
- Test: `frontend-app/src/api/grading.test.js` (create)

- [ ] **Step 1: Write the failing test**

Create `frontend-app/src/api/grading.test.js` (mirror `src/api/endings.test.js`):

```javascript
import { describe, it, expect, vi, beforeEach } from "vitest";
import * as grading from "./grading";

beforeEach(() => {
  global.fetch = vi.fn(() =>
    Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}) })
  );
});

describe("grading api", () => {
  it("getConfig hits /grading/config", async () => {
    await grading.getConfig();
    expect(fetch.mock.calls[0][0]).toContain("/grading/config");
  });

  it("getQuestion passes grading_types + exclude_word_id", async () => {
    await grading.getQuestion({ grading_types: "proste,opisowe", exclude_word_id: 5 });
    const url = fetch.mock.calls[0][0];
    expect(url).toContain("/grading/question?");
    expect(url).toContain("grading_types=proste%2Copisowe");
    expect(url).toContain("exclude_word_id=5");
  });

  it("validate POSTs to /grading/validate", async () => {
    await grading.validate({ word_id: 1, answer: "lepszy", correct_answer: "lepszy" });
    const [url, opts] = fetch.mock.calls[0];
    expect(url).toContain("/grading/validate");
    expect(opts.method).toBe("POST");
  });

  it("getStats hits /grading/stats", async () => {
    await grading.getStats();
    expect(fetch.mock.calls[0][0]).toContain("/grading/stats");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend-app && npx vitest run src/api/grading.test.js`
Expected: FAIL — cannot resolve `./grading`.

- [ ] **Step 3: Write the client**

Create `frontend-app/src/api/grading.js`:

```javascript
import { apiFetch } from "./base";

export const getConfig = () => apiFetch("/grading/config");

export const getQuestion = ({ grading_types, exclude_word_id } = {}) => {
  const params = new URLSearchParams();
  if (grading_types !== undefined && grading_types !== null) {
    params.set("grading_types", grading_types);
  }
  if (exclude_word_id !== undefined && exclude_word_id !== null) {
    params.set("exclude_word_id", exclude_word_id);
  }
  return apiFetch(`/grading/question?${params}`);
};

export const validate = ({ word_id, answer, correct_answer }) =>
  apiFetch("/grading/validate", {
    method: "POST",
    body: { word_id, answer, correct_answer },
  });

export const getStats = () => apiFetch("/grading/stats");
```

- [ ] **Step 4: Re-export from the API index**

In `frontend-app/src/api/index.js`, after the endings re-export line (`export * as endings from "./endings";`), add:

```javascript
export * as grading from "./grading";
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd frontend-app && npx vitest run src/api/grading.test.js`
Expected: PASS (4 passed).

- [ ] **Step 6: Commit**

```bash
git add frontend-app/src/api/grading.js frontend-app/src/api/index.js frontend-app/src/api/grading.test.js
git commit -m "feat(frontend): grading API client + tests"
```

---

## Task 10: Frontend nav card, route, state, handlers, and view

**Files:**
- Modify: `frontend-app/src/App.jsx`

This task adds an inline grading view cloned from the Endings view. Follow the existing Endings code (nav card `App.jsx:646`, valid-views arrays lines 28 & 47, endings state ~lines 69–80, endings fetch/handlers, and the endings view JSX ~lines 841–987) as the structural template. Concrete additions below.

- [ ] **Step 1: Add "grading" to both valid-views arrays**

In `frontend-app/src/App.jsx`, line 28 and line 47, add `"grading"` to each `valid` array:

```javascript
const valid = ["home", "add", "practice", "pronunciation", "endings", "grading", "manage", "admin", "stats-detail"];
```

- [ ] **Step 2: Import the grading client**

Find the import that pulls the API namespace (where `endings` is imported from `./api`). Add `grading` alongside it. If the file imports `import { ... , endings } from "./api";`, change to include `grading`:

```javascript
import { /* existing names */, endings, grading } from "./api";
```

(If endings is referenced as `api.endings`, then use `api.grading` and skip this step.)

- [ ] **Step 3: Add grading view state**

After the endings state block (`App.jsx` ~line 80), add:

```javascript
  // Grading state
  const [gradingConfig, setGradingConfig] = useState(null);
  const [gradingTypes, setGradingTypes] = useState(["nieregularne"]);
  const [gradingMode, setGradingMode] = useState("choose"); // choose | write
  const [gradingQuestion, setGradingQuestion] = useState(null);
  const [gradingStatus, setGradingStatus] = useState(null);
  const [gradingWriteAnswer, setGradingWriteAnswer] = useState("");
  const [gradingStats, setGradingStats] = useState(null);
  const [showGradingGrammar, setShowGradingGrammar] = useState(false);
```

- [ ] **Step 4: Add fetch functions**

Near the endings fetch functions (`fetchEndingsConfig` etc., ~lines 128–152), add:

```javascript
  const fetchGradingConfig = async () => {
    const cfg = await grading.getConfig();
    if (cfg) setGradingConfig(cfg);
  };

  const fetchGradingStats = async () => {
    const s = await grading.getStats();
    if (s) setGradingStats(s);
  };

  const fetchGradingQuestion = async () => {
    const q = await grading.getQuestion({
      grading_types: gradingTypes.join(","),
      exclude_word_id: gradingQuestion?.word_id ?? null,
    });
    setGradingQuestion(q || null);
    setGradingStatus(null);
    setGradingWriteAnswer("");
  };
```

- [ ] **Step 5: Add the effect that loads grading when the page opens**

Near the endings `useEffect` (~line 334), add a dedicated effect:

```javascript
  useEffect(() => {
    if (activePage === "grading") {
      fetchGradingConfig();
      fetchGradingStats();
      fetchGradingQuestion();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activePage, gradingTypes]);
```

- [ ] **Step 6: Add the answer + skip + toggle handlers**

Near the endings handlers (~lines 504–540), add:

```javascript
  const submitGrading = async (answer) => {
    if (!gradingQuestion) return;
    const p = await grading.validate({
      word_id: gradingQuestion.word_id,
      answer,
      correct_answer: gradingQuestion.correct_answer,
    });
    if (!p) { setGradingStatus("Could not validate."); return; }
    setGradingStatus(p.was_correct ? "Correct!" : `Incorrect — ${p.correct_answer}`);
    setGradingStats(p.stats);
    setTimeout(fetchGradingQuestion, 900);
  };

  const handleGradingAnswer = (selected) => submitGrading(selected);
  const handleGradingSkip = () => submitGrading("");

  const toggleGradingType = (t) => {
    setGradingTypes((prev) =>
      prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]
    );
  };
```

- [ ] **Step 7: Add the Home nav card**

In `frontend-app/src/App.jsx`, after the Endings nav card (`</button>` at line 650), add:

```jsx
              <button className="nav-card" onClick={() => setActivePage("grading")} type="button">
                <p className="subtitle">Stopniowanie</p>
                <h3>Grade adjectives</h3>
                <p>Proste, nieregularne, opisowe — comparative &amp; superlative forms.</p>
              </button>
```

- [ ] **Step 8: Add the grading view**

Find where pages are rendered as `activePage === "endings" && (...)`. Immediately after that block, add a `activePage === "grading"` block:

```jsx
            {activePage === "grading" && (
              <section className="panel">
                <button className="link-btn" onClick={() => setActivePage("home")} type="button">← Back</button>
                <h2>Stopniowanie przymiotników</h2>

                <div className="chip-row">
                  {["proste", "nieregularne", "opisowe"].map((t) => (
                    <button
                      key={t}
                      type="button"
                      className={`chip ${gradingTypes.includes(t) ? "chip-on" : ""}`}
                      onClick={() => toggleGradingType(t)}
                    >
                      {t}{gradingConfig?.counts?.[t] != null ? ` (${gradingConfig.counts[t]})` : ""}
                    </button>
                  ))}
                </div>

                <div className="chip-row">
                  <button type="button" className={`chip ${gradingMode === "choose" ? "chip-on" : ""}`} onClick={() => setGradingMode("choose")}>Choose</button>
                  <button type="button" className={`chip ${gradingMode === "write" ? "chip-on" : ""}`} onClick={() => setGradingMode("write")}>Write</button>
                </div>

                {gradingStats && (
                  <p className="subtitle">Today: {gradingStats.today_percentage}% · Overall: {gradingStats.overall_percentage}% · {gradingStats.available_words} adjectives</p>
                )}

                {gradingStatus && <p className="status">{gradingStatus}</p>}

                {gradingQuestion ? (
                  <div className="question-card">
                    <p className="subtitle">
                      {gradingQuestion.grading_type} · {gradingQuestion.degree === "comparative" ? "stopień wyższy" : "stopień najwyższy"}
                    </p>
                    <h3>{gradingQuestion.positive} <span className="subtitle">({gradingQuestion.english})</span></h3>

                    {gradingMode === "choose" ? (
                      <div className="options-grid">
                        {gradingQuestion.options.map((opt) => (
                          <button key={opt} type="button" className="option-btn" onClick={() => handleGradingAnswer(opt)}>{opt}</button>
                        ))}
                      </div>
                    ) : (
                      <form onSubmit={(e) => { e.preventDefault(); handleGradingAnswer(gradingWriteAnswer); }}>
                        <input
                          className="text-input"
                          value={gradingWriteAnswer}
                          onChange={(e) => setGradingWriteAnswer(e.target.value)}
                          placeholder="Type the form…"
                          autoFocus
                        />
                        <button type="submit" className="primary-btn">Check</button>
                      </form>
                    )}

                    <button type="button" className="link-btn" onClick={handleGradingSkip}>Skip</button>

                    <button type="button" className="link-btn" onClick={() => setShowGradingGrammar((v) => !v)}>
                      {showGradingGrammar ? "Hide" : "Show"} grammar reference
                    </button>
                    {showGradingGrammar && gradingQuestion.grammar_reference?.grading_rules && (
                      <div className="grammar-ref">
                        <p>{gradingQuestion.grammar_reference.grading_rules.rule}</p>
                        <p className="subtitle">{gradingQuestion.grammar_reference.grading_rules.examples}</p>
                      </div>
                    )}
                  </div>
                ) : (
                  <p>No adjectives for the selected types. Pick another type.</p>
                )}
              </section>
            )}
```

> **Note:** Class names above (`panel`, `chip`, `chip-on`, `question-card`, `options-grid`, `option-btn`, `grammar-ref`, `status`, `text-input`, `primary-btn`, `link-btn`) are reused from the Endings view. If any differ in the actual file, match the Endings view's class names exactly — do not invent new CSS.

- [ ] **Step 9: Run the frontend suite (no regressions)**

Run: `cd frontend-app && npx vitest run`
Expected: all pass (existing + new grading api tests).

- [ ] **Step 10: Manual smoke check**

Start backend + frontend, open the app, click the new "Stopniowanie" card. Verify: types togglable with counts, a question renders, choosing an option shows Correct/Incorrect, stats update, grammar reference toggles, Write mode accepts text. (See the `/run` or `/verify` skill to drive the app.)

- [ ] **Step 11: Commit**

```bash
git add frontend-app/src/App.jsx
git commit -m "feat(frontend): Stopniowanie section — nav card, route, grading view"
```

---

## Backlog (out of scope — raised in review)

- **Case/gender declension of graded forms** (v2): comparatives inflect (`lepszy → lepszego → lepszej`); this feature does nominative base only.
- **App.jsx page-extraction refactor**: extract each inline page (Endings, Grading, Practice, …) into `src/components/pages/*` with a shared `useExerciseView` hook + `GrammarPanel`/answer components. Flagged by frontend review as growing debt; not a blocker for this feature.

---

## Self-Review Notes

- **Spec coverage:** data model (T1/T2), seed (T5), grammar rules (T3), distractor LLM cache (T4/T7), all four endpoints (T7), stats (T7), frontend section (T9/T10), tests (T1,T3,T4,T5,T8,T9). ✅
- **No migration for `AttemptKind.grading`** — enum-only change, per codebase note. ✅
- **Type consistency:** `generate_grading_distractors_via_llm(positive, correct, degree, grading_type)` signature identical in T4 real fn, T4 fake, and T7 caller. `GradingQuestion` fields identical in T6 schema and T7 response. Client `getQuestion({ grading_types, exclude_word_id })` matches T9 test and T10 caller. ✅
