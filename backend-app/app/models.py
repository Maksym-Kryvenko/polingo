from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class LanguageSet(str, Enum):
    english = "english"
    ukrainian = "ukrainian"


class PracticeDirection(str, Enum):
    translation = "translation"
    writing = "writing"


class WordLanguage(str, Enum):
    polish = "polish"
    english = "english"
    ukrainian = "ukrainian"


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


class WordOption(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("word_id", "language", "value"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    word_id: int = Field(foreign_key="word.id")
    language: WordLanguage
    value: str = Field(index=True)


class UserSession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    language_set: LanguageSet = Field(default=LanguageSet.english)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserSessionWord(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("session_id", "word_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="usersession.id")
    word_id: int = Field(foreign_key="word.id")
    added_at: datetime = Field(default_factory=datetime.utcnow)
