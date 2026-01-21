from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class LanguageSet(str, Enum):
    english = "english"
    ukrainian = "ukrainian"


class PracticeDirection(str, Enum):
    translation = "translation"
    writing = "writing"


class Word(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    polish: str = Field(index=True)
    english: str
    ukrainian: str


class PracticeRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    word_id: int = Field(foreign_key="word.id")
    language_set: LanguageSet
    direction: PracticeDirection
    was_correct: bool
    practice_date: date = Field(default_factory=date.today)
    created_at: datetime = Field(default_factory=datetime.utcnow)
