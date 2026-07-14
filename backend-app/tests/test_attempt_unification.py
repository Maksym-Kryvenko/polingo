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
