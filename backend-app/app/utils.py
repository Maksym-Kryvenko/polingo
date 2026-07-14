from datetime import date, timedelta
import re
import unicodedata

from sqlalchemy import func
from sqlmodel import Session, select

from app.models import Attempt, Word
from app.schemas import StatsResponse


def calculate_stats(session: Session) -> StatsResponse:
    """Unified stats over the single Attempt table (M3)."""
    today = date.today()
    yesterday = today - timedelta(days=1)

    def aggregation(target_date: date) -> tuple[int, int]:
        rows = session.exec(
            select(Attempt).where(Attempt.practice_date == target_date)
        ).all()
        return sum(r.was_correct for r in rows), len(rows)

    today_correct, today_total = aggregation(today)
    yesterday_correct, yesterday_total = aggregation(yesterday)

    all_rows = session.exec(select(Attempt)).all()
    overall_total = len(all_rows)
    overall_correct = sum(r.was_correct for r in all_rows)

    word_count = session.scalar(select(func.count()).select_from(Word)) or 0

    def percent(correct: int, total: int) -> float:
        return (correct / total) * 100.0 if total else 0.0

    today_percent = percent(today_correct, today_total)
    yesterday_percent = percent(yesterday_correct, yesterday_total)
    overall_percent = percent(overall_correct, overall_total)
    return StatsResponse(
        today_percentage=round(today_percent, 1),
        trend=round(today_percent - yesterday_percent, 1),
        overall_percentage=round(overall_percent, 1),
        available_words=int(word_count),
    )


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value or "")
    normalized = re.sub(r"[\u0300-\u036f]", "", normalized)
    return normalized.strip().lower()
