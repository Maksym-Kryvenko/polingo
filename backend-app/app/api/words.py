from sqlalchemy import func
from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from app.database import engine
from app.models import Word, UserSession, UserSessionWord
from app.schemas import (
    WordCheckRequest,
    WordCheckResponse,
    WordCheckBulkRequest,
    WordCheckBulkResponse,
    WordCheckResult,
    WordRead,
)
from app.llm import resolve_word_via_llm

router = APIRouter(prefix="/words", tags=["words"])


@router.get("/initial", response_model=list[WordRead])
def get_initial_words(count: int = 10) -> list[WordRead]:
    with Session(engine) as session:
        return session.exec(select(Word).limit(count)).all()


@router.post("/check", response_model=WordCheckResponse)
def check_word(payload: WordCheckRequest) -> WordCheckResponse:
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Value is required")

    normalized = text.lower().strip()
    with Session(engine) as session:
        for field in ("polish", "english", "ukrainian"):
            statement = select(Word).where(
                func.lower(getattr(Word, field)) == normalized
            )
            word = session.exec(statement).first()
            if word:
                return WordCheckResponse(
                    found=True,
                    word=word,
                    matched_field=field,
                    created=False,
                    source="database",
                )

        try:
            resolved = resolve_word_via_llm(text)
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        required_fields = ("polish", "english", "ukrainian")
        if not all(resolved.get(field) for field in required_fields):
            raise HTTPException(
                status_code=422, detail="Unable to resolve translations"
            )

        resolved_normalized = {
            field: resolved[field].lower().strip() for field in required_fields
        }
        for field, normalized_value in resolved_normalized.items():
            statement = select(Word).where(
                func.lower(getattr(Word, field)) == normalized_value
            )
            word = session.exec(statement).first()
            if word:
                return WordCheckResponse(
                    found=True,
                    word=word,
                    matched_field=field,
                    created=False,
                    source="database",
                )

        new_word = Word(
            polish=resolved["polish"],
            english=resolved["english"],
            ukrainian=resolved["ukrainian"],
        )
        session.add(new_word)
        session.commit()
        session.refresh(new_word)
        return WordCheckResponse(
            found=True,
            word=new_word,
            matched_field="resolved",
            created=True,
            source="llm",
        )


def get_or_create_session(session: Session) -> UserSession:
    """Get or create the user session."""
    state = session.exec(select(UserSession)).first()
    if not state:
        state = UserSession()
        session.add(state)
        session.commit()
        session.refresh(state)
    return state


def check_single_word(
    session: Session, text: str, session_word_ids: set[int]
) -> WordCheckResult:
    """Check a single word and return the result."""
    normalized = text.lower().strip()

    # Check if already exists in database
    for field in ("polish", "english", "ukrainian"):
        statement = select(Word).where(func.lower(getattr(Word, field)) == normalized)
        word = session.exec(statement).first()
        if word:
            is_duplicate = word.id in session_word_ids
            return WordCheckResult(
                text=text,
                found=True,
                word=WordRead.model_validate(word),
                matched_field=field,
                created=False,
                source="database",
                duplicate=is_duplicate,
            )

    # Try LLM resolution
    try:
        resolved = resolve_word_via_llm(text)
    except RuntimeError:
        return WordCheckResult(
            text=text,
            found=False,
            source="llm_error",
        )

    required_fields = ("polish", "english", "ukrainian")
    if not all(resolved.get(field) for field in required_fields):
        return WordCheckResult(
            text=text,
            found=False,
            source="llm_incomplete",
        )

    # Check if resolved word already exists
    resolved_normalized = {
        field: resolved[field].lower().strip() for field in required_fields
    }
    for field, normalized_value in resolved_normalized.items():
        statement = select(Word).where(
            func.lower(getattr(Word, field)) == normalized_value
        )
        word = session.exec(statement).first()
        if word:
            is_duplicate = word.id in session_word_ids
            return WordCheckResult(
                text=text,
                found=True,
                word=WordRead.model_validate(word),
                matched_field=field,
                created=False,
                source="database",
                duplicate=is_duplicate,
            )

    # Create new word
    new_word = Word(
        polish=resolved["polish"],
        english=resolved["english"],
        ukrainian=resolved["ukrainian"],
    )
    session.add(new_word)
    session.commit()
    session.refresh(new_word)

    return WordCheckResult(
        text=text,
        found=True,
        word=WordRead.model_validate(new_word),
        matched_field="resolved",
        created=True,
        source="llm",
        duplicate=False,
    )


@router.post("/check/bulk", response_model=WordCheckBulkResponse)
def check_words_bulk(payload: WordCheckBulkRequest) -> WordCheckBulkResponse:
    """Check multiple comma-separated words/phrases and add them to session."""
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Value is required")

    # Split by comma and clean up
    words_to_check = [w.strip() for w in text.split(",") if w.strip()]

    if not words_to_check:
        raise HTTPException(status_code=400, detail="No valid words found")

    results: list[WordCheckResult] = []
    added_count = 0
    duplicate_count = 0
    failed_count = 0

    with Session(engine) as session:
        user_session = get_or_create_session(session)

        # Get existing session word IDs
        existing_session_words = session.exec(
            select(UserSessionWord.word_id).where(
                UserSessionWord.session_id == user_session.id
            )
        ).all()
        session_word_ids = set(existing_session_words)

        for word_text in words_to_check:
            result = check_single_word(session, word_text, session_word_ids)
            results.append(result)

            if result.found and result.word:
                if result.duplicate:
                    duplicate_count += 1
                else:
                    # Add to session
                    session.add(
                        UserSessionWord(
                            session_id=user_session.id,
                            word_id=result.word.id,
                        )
                    )
                    session_word_ids.add(result.word.id)
                    added_count += 1
            else:
                failed_count += 1

        session.commit()

    return WordCheckBulkResponse(
        results=results,
        added_count=added_count,
        duplicate_count=duplicate_count,
        failed_count=failed_count,
    )
