from typing import Optional

from pydantic import ConfigDict
from sqlmodel import SQLModel

from app.models import LanguageSet, PracticeDirection, Word


class WordRead(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    polish: str
    english: str
    ukrainian: str


class WordCheckRequest(SQLModel):
    text: str


class WordCheckResponse(SQLModel):
    found: bool
    word: Optional[WordRead]
    matched_field: Optional[str]


class PracticeSubmission(SQLModel):
    word_id: int
    language_set: LanguageSet
    direction: PracticeDirection
    was_correct: bool


class StatsResponse(SQLModel):
    today_percentage: float
    trend: float
    overall_percentage: float
    available_words: int
