from datetime import date, timedelta

from sqlalchemy import func
from sqlmodel import Session, select

from app.models import PracticeRecord, Word
from app.schemas import StatsResponse


def calculate_stats(session: Session) -> StatsResponse:
    today = date.today()
    yesterday = today - timedelta(days=1)

    def aggregation(target_date: date) -> tuple[int, int]:
        records = session.exec(
            select(PracticeRecord).where(PracticeRecord.practice_date == target_date)
        ).all()
        total = len(records)
        correct = sum(record.was_correct for record in records)
        return correct, total

    today_correct, today_total = aggregation(today)
    yesterday_correct, yesterday_total = aggregation(yesterday)

    overall_records = session.exec(select(PracticeRecord)).all()
    overall_total = len(overall_records)
    overall_correct = sum(record.was_correct for record in overall_records)

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
