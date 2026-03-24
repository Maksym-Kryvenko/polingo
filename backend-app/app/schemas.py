from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import ConfigDict
from sqlmodel import SQLModel

from app.models import LanguageSet, PracticeDirection, WordLanguage


# ── Word schemas ─────────────────────────────────────────────


class WordRead(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    polish: str
    english: str
    ukrainian: str
    part_of_speech: str = "inne"
    gender: Optional[str] = None


class WordWithStats(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    polish: str
    english: str
    ukrainian: str
    part_of_speech: str = "inne"
    gender: Optional[str] = None
    total_attempts: int = 0
    correct_attempts: int = 0
    error_rate: float = 0.0
    enabled: bool = True


class WordUpdateRequest(SQLModel):
    polish: str
    english: str
    ukrainian: str


class WordCheckRequest(SQLModel):
    text: str


class WordCheckBulkRequest(SQLModel):
    text: str


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
    word: Optional[WordRead] = None
    matched_field: Optional[str] = None
    created: bool = False
    source: Optional[str] = None


# ── Practice schemas ─────────────────────────────────────────


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
    alternatives: list[str] = []
    stats: StatsResponse


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


# ── Session schemas ──────────────────────────────────────────


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


class WordToggleRequest(SQLModel):
    word_id: int
    enabled: bool


# ── Choose Translation schemas ───────────────────────────────


class TranslationQuestion(SQLModel):
    word_id: int
    polish: str
    english: str
    ukrainian: str
    prompt: str
    correct_answer: str
    options: list[str]
    direction: str


class TranslationValidationRequest(SQLModel):
    word_id: int
    language_set: LanguageSet
    direction: str
    answer: str


class TranslationValidationResponse(SQLModel):
    was_correct: bool
    correct_answer: str
    stats: StatsResponse


# ── Endings practice schemas ─────────────────────────────────


class EndingsQuestion(SQLModel):
    word_id: int
    polish: str
    english: str
    ukrainian: str
    part_of_speech: str
    sentence: str          # sentence with ___ placeholder
    correct_answer: str
    options: list[str]     # 4 options (for choose mode)
    # Context fields
    case: Optional[str] = None
    gender: Optional[str] = None
    number: Optional[str] = None
    pronoun: Optional[str] = None
    tense: Optional[str] = None
    grammar_reference: dict[str, Any] = {}


class EndingsValidationRequest(SQLModel):
    word_id: int
    sentence_id: Optional[int] = None
    answer: str
    correct_answer: str  # sent back from question for verification


class EndingsValidationResponse(SQLModel):
    was_correct: bool
    correct_answer: str
    stats: EndingsStatsResponse


class EndingsStatsResponse(SQLModel):
    today_percentage: float
    trend: float
    overall_percentage: float
    available_words: int


class EndingsConfigResponse(SQLModel):
    """Available options for endings practice configuration."""
    parts_of_speech: list[str]
    cases: list[str]
    tenses: list[str]


# ── History schemas ──────────────────────────────────────────


class HistoryRecord(SQLModel):
    id: int
    word_polish: str
    word_translation: str
    section: str  # "translation", "writing", "pronunciation", "endings"
    was_correct: bool
    created_at: datetime
    user_answer: Optional[str] = None
    correct_answer: Optional[str] = None


class HistoryResponse(SQLModel):
    records: list[HistoryRecord]
    total: int


class ExplainRequest(SQLModel):
    word_polish: str
    word_translation: str
    section: str
    user_answer: Optional[str] = None
    correct_answer: Optional[str] = None
    was_correct: bool


class ExplainResponse(SQLModel):
    explanation: str


# ── Admin schemas ────────────────────────────────────────────


class DeviceRead(SQLModel):
    id: int
    ip_address: str
    user_agent: str
    device_type: str
    browser: str
    os: str
    first_seen: datetime
    last_activity: datetime
    request_count: int
    is_active: bool


class DevicesResponse(SQLModel):
    devices: list[DeviceRead]
    total_count: int
    active_count: int


class AppSettingRead(SQLModel):
    key: str
    value: str


class AppSettingUpdate(SQLModel):
    value: str


# ── Sentence management schemas ──────────────────────────────


class PracticeSentenceRead(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    word_id: int
    word_polish: str = ""
    part_of_speech: str
    sentence: str
    correct_answer: str
    case: Optional[str] = None
    gender: Optional[str] = None
    number: Optional[str] = None
    pronoun: Optional[str] = None
    tense: Optional[str] = None


class PracticeSentenceUpdate(SQLModel):
    sentence: Optional[str] = None
    correct_answer: Optional[str] = None


class SentenceFixRequest(SQLModel):
    sentence_id: int
