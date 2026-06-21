import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.database import engine
from main import app  # root conftest.py uses this exact import; main.py defines `app`
from app.models import AppSetting, UserSession, UserSessionWord, Word
from app.seed import seed_words


@pytest.fixture
def seeded_client():
    """A TestClient backed by a freshly-seeded in-memory DB.

    fresh_db (root conftest, autouse) has already dropped+created the schema for
    this test (autouse fixtures run before requested ones at the same scope). We
    seed the canonical words + a default session + the AppSettings that init_db()
    would create, AND attach the first 6 words to the session so endpoints that
    require a populated session (choose-translation needs >=4) behave like prod.
    The in-memory engine uses StaticPool, so this session and the TestClient
    request handlers share one DB.
    """
    with Session(engine) as session:
        seed_words(session)  # fresh_db guarantees empty tables; no guard needed
        user_session = UserSession()
        session.add(user_session)
        session.commit()
        session.refresh(user_session)
        first_words = session.exec(select(Word).limit(6)).all()
        for w in first_words:
            session.add(UserSessionWord(session_id=user_session.id, word_id=w.id, enabled=True))
        for key, value in (("generate_on_the_fly", "false"), ("tts_source", "browser")):
            session.add(AppSetting(key=key, value=value))
        session.commit()
    return TestClient(app)
