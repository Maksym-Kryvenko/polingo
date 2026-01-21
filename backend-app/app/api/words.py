from sqlalchemy import func
from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from app.database import engine
from app.models import Word
from app.schemas import WordCheckRequest, WordCheckResponse, WordRead


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

    normalized = text.lower()
    with Session(engine) as session:
        for field in ("polish", "english", "ukrainian"):
            statement = select(Word).where(func.lower(getattr(Word, field)) == normalized)
            word = session.exec(statement).first()
            if word:
                return WordCheckResponse(found=True, word=word, matched_field=field)

    return WordCheckResponse(found=False, word=None, matched_field=None)
