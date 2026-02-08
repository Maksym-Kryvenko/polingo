from __future__ import annotations

from datetime import datetime
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
    enabled: bool = True


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
    alternatives: list[str] = []
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


# Verb/Endings schemas
class VerbAddRequest(SQLModel):
    text: str  # Verb in English or Ukrainian
    source_language: str  # "english" or "ukrainian"


class VerbConjugationRead(SQLModel):
    pronoun: str
    conjugated_form: str


class VerbRead(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    infinitive: str
    english: str
    ukrainian: str


class VerbWithConjugations(SQLModel):
    id: int
    infinitive: str
    english: str
    ukrainian: str
    conjugations: list[VerbConjugationRead]
    total_attempts: int = 0
    correct_attempts: int = 0
    error_rate: float = 0.0
    enabled: bool = True


class VerbAddResponse(SQLModel):
    success: bool
    verb: Optional[VerbWithConjugations] = None
    message: str
    duplicate: bool = False


class VerbSessionState(SQLModel):
    verbs: list[VerbWithConjugations]


class EndingsQuestion(SQLModel):
    verb_id: int
    infinitive: str
    english: str
    ukrainian: str
    pronoun: str
    correct_answer: str
    options: list[str]  # 4 shuffled options including correct


class EndingsValidationRequest(SQLModel):
    verb_id: int
    pronoun: str
    answer: str


class EndingsValidationResponse(SQLModel):
    was_correct: bool
    correct_answer: str
    stats: "EndingsStatsResponse"


class EndingsStatsResponse(SQLModel):
    today_percentage: float
    trend: float
    overall_percentage: float
    available_verbs: int


class WordToggleRequest(SQLModel):
    word_id: int
    enabled: bool


class VerbToggleRequest(SQLModel):
    verb_id: int
    enabled: bool


# Choose Translation schemas
class TranslationQuestion(SQLModel):
    word_id: int
    polish: str
    english: str
    ukrainian: str
    prompt: str  # The word to translate (source)
    correct_answer: str  # The correct translation (target)
    options: list[str]  # 4 shuffled options including correct
    direction: str  # "from_polish" or "to_polish"


class TranslationValidationRequest(SQLModel):
    word_id: int
    language_set: LanguageSet
    direction: str  # "from_polish" or "to_polish"
    answer: str


class TranslationValidationResponse(SQLModel):
    was_correct: bool
    correct_answer: str
    stats: "StatsResponse"


# Admin/Device tracking schemas
class DeviceRead(SQLModel):
    id: int
    ip_address: str
    user_agent: str
    device_type: str
    browser: str
    os: str
    first_seen: "datetime"
    last_activity: "datetime"
    request_count: int
    is_active: bool


class DevicesResponse(SQLModel):
    devices: list[DeviceRead]
    total_count: int
    active_count: int
