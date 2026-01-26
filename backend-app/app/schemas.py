from __future__ import annotations

from typing import Optional

from pydantic import ConfigDict
from sqlmodel import SQLModel

from app.models import LanguageSet, PracticeDirection, WordLanguage


class WordRead(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    polish: str
    english: str
    ukrainian: str


class WordWithStats(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    polish: str
    english: str
    ukrainian: str
    total_attempts: int = 0
    correct_attempts: int = 0
    error_rate: float = 0.0  # Higher = more errors


class WordCheckRequest(SQLModel):
    text: str


class WordCheckBulkRequest(SQLModel):
    text: str  # Comma-separated words/phrases


class WordCheckResult(SQLModel):
    text: str
    found: bool
    word: Optional[WordRead] = None
    matched_field: Optional[str] = None
    created: bool = False
    source: Optional[str] = None
    duplicate: bool = False


class WordCheckBulkResponse(SQLModel):
    results: list[WordCheckResult]
    added_count: int
    duplicate_count: int
    failed_count: int


class WordCheckResponse(SQLModel):
    found: bool
    word: Optional[WordRead]
    matched_field: Optional[str]
    created: bool = False
    source: Optional[str] = None


class PracticeSubmission(SQLModel):
    word_id: int
    language_set: LanguageSet
    direction: PracticeDirection
    was_correct: bool


class PracticeValidationRequest(SQLModel):
    word_id: int
    language_set: LanguageSet
    direction: PracticeDirection
    answer: str


class PracticeValidationResponse(SQLModel):
    was_correct: bool
    correct_answer: str
    matched_via: Optional[str] = None
    stats: "StatsResponse"


class SessionWordAdd(SQLModel):
    word_id: int


class SessionWordBulkAdd(SQLModel):
    word_ids: list[int]


class SessionLanguageUpdate(SQLModel):
    language_set: LanguageSet


class SessionState(SQLModel):
    language_set: LanguageSet
    words: list[WordWithStats]


class WordOptionRead(SQLModel):
    word_id: int
    language: WordLanguage
    value: str


class StatsResponse(SQLModel):
    today_percentage: float
    trend: float
    overall_percentage: float
    available_words: int


class PronunciationValidationResponse(SQLModel):
    was_correct: bool
    expected_word: str
    transcribed_text: str
    feedback: str
    similarity_score: float
    stats: StatsResponse
