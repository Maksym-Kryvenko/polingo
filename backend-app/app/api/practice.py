from fastapi import APIRouter
from sqlmodel import Session

from app.database import engine
from app.models import PracticeRecord
from app.schemas import PracticeSubmission, StatsResponse
from app.utils import calculate_stats


router = APIRouter(prefix="/practice", tags=["practice"])


@router.post("/submit", response_model=StatsResponse)
def submit_practice(payload: PracticeSubmission) -> StatsResponse:
    with Session(engine) as session:
        session.add(PracticeRecord(**payload.model_dump()))
        session.commit()
        return calculate_stats(session)
