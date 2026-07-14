from fastapi import APIRouter, HTTPException, Query
from sqlmodel import Session, select

from app.database import engine
from app import config
from app.llm import get_openai_client
from app.models import Attempt, AttemptKind, Word
from app.schemas import (
    ExplainRequest,
    ExplainResponse,
    HistoryRecord,
    HistoryResponse,
    StatsResponse,
)
from app.utils import calculate_stats


router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=StatsResponse)
def read_stats() -> StatsResponse:
    with Session(engine) as session:
        return calculate_stats(session)


@router.get("/history", response_model=HistoryResponse)
def get_history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    language_set: str = Query("english"),
) -> HistoryResponse:
    """Return unified practice history across all sections."""
    with Session(engine) as session:
        rows = session.exec(
            select(Attempt).order_by(Attempt.created_at.desc())
        ).all()
        records: list[HistoryRecord] = []
        for r in rows:
            word = session.get(Word, r.word_id)
            word_polish = word.polish if word else "?"
            word_translation = getattr(word, language_set, "?") if word else "?"
            if r.kind == AttemptKind.practice and r.direction is not None:
                section = r.direction.value
            else:
                section = "endings"
            records.append(HistoryRecord(
                id=r.id,
                word_polish=word_polish,
                word_translation=word_translation,
                section=section,
                was_correct=r.was_correct,
                created_at=r.created_at,
                user_answer=r.user_answer,
                correct_answer=r.correct_answer,
            ))

        total = len(records)
        page = records[offset:offset + limit]
        return HistoryResponse(records=page, total=total)


@router.post("/explain", response_model=ExplainResponse)
def explain_answer(payload: ExplainRequest) -> ExplainResponse:
    """Use LLM to explain a historical practice answer."""
    try:
        client = get_openai_client()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    prompt = (
        "You are a Polish language tutor. The learner practiced a word and you need to explain "
        "the answer clearly. Include why the correct answer is right, explain grammar rules if relevant, "
        "and give tips to remember. Keep it concise (2-4 sentences). Answer in English."
    )
    user_msg_parts = [
        f"Polish word: {payload.word_polish}",
        f"Translation: {payload.word_translation}",
        f"Practice section: {payload.section}",
        f"Was correct: {payload.was_correct}",
    ]
    if payload.correct_answer:
        user_msg_parts.append(f"Correct answer: {payload.correct_answer}")
    if payload.user_answer:
        user_msg_parts.append(f"Learner's answer: {payload.user_answer}")

    response = client.responses.create(
        model=config.text_model(),
        instructions=prompt,
        input="\n".join(user_msg_parts),
    )
    explanation = response.output_text or "Could not generate explanation."
    return ExplainResponse(explanation=explanation)
