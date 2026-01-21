from fastapi import APIRouter
from sqlmodel import Session

from app.database import engine
from app.utils import calculate_stats
from app.schemas import StatsResponse


router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=StatsResponse)
def read_stats() -> StatsResponse:
    with Session(engine) as session:
        return calculate_stats(session)
