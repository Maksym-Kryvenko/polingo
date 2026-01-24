from sqlalchemy import func
from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from app.database import engine
from app.models import Word
from app.schemas import WordCheckRequest, WordCheckResponse, WordRead
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
