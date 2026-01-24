from datetime import datetime

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from app.database import engine
from app.models import UserSession, UserSessionWord, Word
from app.schemas import (
    SessionLanguageUpdate,
    SessionState,
    SessionWordAdd,
    SessionWordBulkAdd,
)

router = APIRouter(prefix="/session", tags=["session"])


def get_or_create_session(session: Session) -> UserSession:
    state = session.exec(select(UserSession)).first()
    if not state:
        state = UserSession()
        session.add(state)
        session.commit()
        session.refresh(state)
    return state


@router.get("", response_model=SessionState)
def get_session_state() -> SessionState:
    with Session(engine) as session:
        state = get_or_create_session(session)
        words = session.exec(
            select(Word)
            .join(UserSessionWord, UserSessionWord.word_id == Word.id)
            .where(UserSessionWord.session_id == state.id)
            .order_by(UserSessionWord.added_at)
        ).all()
        return SessionState(language_set=state.language_set, words=words)


@router.put("/language", response_model=SessionState)
def update_language(payload: SessionLanguageUpdate) -> SessionState:
    with Session(engine) as session:
        state = get_or_create_session(session)
        state.language_set = payload.language_set
        state.updated_at = datetime.utcnow()
        session.add(state)
        session.commit()
        session.refresh(state)
        words = session.exec(
            select(Word)
            .join(UserSessionWord, UserSessionWord.word_id == Word.id)
            .where(UserSessionWord.session_id == state.id)
            .order_by(UserSessionWord.added_at)
        ).all()
        return SessionState(language_set=state.language_set, words=words)


@router.post("/words", response_model=SessionState)
def add_word(payload: SessionWordAdd) -> SessionState:
    with Session(engine) as session:
        state = get_or_create_session(session)
        word = session.get(Word, payload.word_id)
        if not word:
            raise HTTPException(status_code=404, detail="Word not found")
        existing = session.exec(
            select(UserSessionWord).where(
                UserSessionWord.session_id == state.id,
                UserSessionWord.word_id == payload.word_id,
            )
        ).first()
        if not existing:
            session.add(UserSessionWord(session_id=state.id, word_id=payload.word_id))
            session.commit()
        words = session.exec(
            select(Word)
            .join(UserSessionWord, UserSessionWord.word_id == Word.id)
            .where(UserSessionWord.session_id == state.id)
            .order_by(UserSessionWord.added_at)
        ).all()
        return SessionState(language_set=state.language_set, words=words)


@router.post("/words/bulk", response_model=SessionState)
def add_words_bulk(payload: SessionWordBulkAdd) -> SessionState:
    with Session(engine) as session:
        state = get_or_create_session(session)
        for word_id in payload.word_ids:
            word = session.get(Word, word_id)
            if not word:
                raise HTTPException(status_code=404, detail=f"Word {word_id} not found")
            existing = session.exec(
                select(UserSessionWord).where(
                    UserSessionWord.session_id == state.id,
                    UserSessionWord.word_id == word_id,
                )
            ).first()
            if not existing:
                session.add(UserSessionWord(session_id=state.id, word_id=word_id))
        session.commit()
        words = session.exec(
            select(Word)
            .join(UserSessionWord, UserSessionWord.word_id == Word.id)
            .where(UserSessionWord.session_id == state.id)
            .order_by(UserSessionWord.added_at)
        ).all()
        return SessionState(language_set=state.language_set, words=words)
