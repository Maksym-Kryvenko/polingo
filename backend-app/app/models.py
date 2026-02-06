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
    pronunciation = "pronunciation"


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
    enabled: bool = Field(default=True)


class Pronoun(str, Enum):
    ja = "ja"  # I
    ty = "ty"  # you (singular)
    on_ona_ono = "on/ona/ono"  # he/she/it
    my = "my"  # we
    wy = "wy"  # you (plural)
    oni_one = "oni/one"  # they


class Verb(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    infinitive: str = Field(index=True)  # Polish infinitive (e.g., "robić")
    english: str  # English translation (e.g., "to do")
    ukrainian: str  # Ukrainian translation


class VerbConjugation(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("verb_id", "pronoun"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    verb_id: int = Field(foreign_key="verb.id")
    pronoun: Pronoun
    conjugated_form: str  # e.g., "robię" for ja + robić


class VerbPracticeRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    verb_id: int = Field(foreign_key="verb.id")
    pronoun: Pronoun
    was_correct: bool
    practice_date: date = Field(default_factory=date.today)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserSessionVerb(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("session_id", "verb_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="usersession.id")
    verb_id: int = Field(foreign_key="verb.id")
    added_at: datetime = Field(default_factory=datetime.utcnow)
    enabled: bool = Field(default=True)
