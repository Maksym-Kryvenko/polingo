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
