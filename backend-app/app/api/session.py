from datetime import datetime

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, case, desc
from sqlmodel import Session, select

from app.database import engine
from app.models import UserSession, UserSessionWord, Word, PracticeRecord
from app.schemas import (
    SessionLanguageUpdate,
    SessionState,
    SessionWordAdd,
    SessionWordBulkAdd,
    WordWithStats,
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


def get_words_with_stats(session: Session, user_session_id: int) -> list[WordWithStats]:
    """Get words ordered by error rate (highest errors first)."""
    # Subquery for word statistics
    stats_subquery = (
        select(
            PracticeRecord.word_id,
            func.count(PracticeRecord.id).label("total_attempts"),
            func.sum(case((PracticeRecord.was_correct == True, 1), else_=0)).label(
                "correct_attempts"
            ),
        )
        .group_by(PracticeRecord.word_id)
        .subquery()
    )

    # Main query joining words with stats
    statement = (
        select(
            Word.id,
            Word.polish,
            Word.english,
            Word.ukrainian,
            func.coalesce(stats_subquery.c.total_attempts, 0).label("total_attempts"),
            func.coalesce(stats_subquery.c.correct_attempts, 0).label(
                "correct_attempts"
            ),
        )
        .join(UserSessionWord, UserSessionWord.word_id == Word.id)
        .outerjoin(stats_subquery, stats_subquery.c.word_id == Word.id)
        .where(UserSessionWord.session_id == user_session_id)
        .order_by(
            # Order by error rate descending (words with more errors first)
            # error_rate = (total - correct) / total, but handle division by zero
            # Words with no attempts go last
            desc(
                case(
                    (func.coalesce(stats_subquery.c.total_attempts, 0) == 0, -1),
                    else_=(
                        (
                            func.coalesce(stats_subquery.c.total_attempts, 0)
                            - func.coalesce(stats_subquery.c.correct_attempts, 0)
                        )
                        * 1.0
                        / func.coalesce(stats_subquery.c.total_attempts, 1)
                    ),
                )
            ),
            # Secondary sort: more attempts = higher priority
            desc(func.coalesce(stats_subquery.c.total_attempts, 0)),
            # Tertiary: by added_at for new words
            UserSessionWord.added_at,
        )
    )

    rows = session.exec(statement).all()

    words_with_stats = []
    for row in rows:
        total = row.total_attempts or 0
        correct = row.correct_attempts or 0
        error_rate = ((total - correct) / total * 100) if total > 0 else 0.0

        words_with_stats.append(
            WordWithStats(
                id=row.id,
                polish=row.polish,
                english=row.english,
                ukrainian=row.ukrainian,
                total_attempts=total,
                correct_attempts=correct,
                error_rate=round(error_rate, 1),
            )
        )

    return words_with_stats


@router.get("", response_model=SessionState)
def get_session_state() -> SessionState:
    with Session(engine) as session:
        state = get_or_create_session(session)
        words = get_words_with_stats(session, state.id)
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
        words = get_words_with_stats(session, state.id)
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
        words = get_words_with_stats(session, state.id)
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
        words = get_words_with_stats(session, state.id)
        return SessionState(language_set=state.language_set, words=words)
