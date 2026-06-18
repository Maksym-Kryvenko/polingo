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
    # Force the LLM to "approve" a wrong-looking answer.
    # Patch where it's used, not where it's defined (practice.py imports it directly)
    monkeypatch.setattr(
        "app.api.practice.validate_translation_via_llm",
        lambda **kw: {
            "is_correct": True, "normalized_answer": "kota", "rationale": "fake-approve",
        },
    )
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
