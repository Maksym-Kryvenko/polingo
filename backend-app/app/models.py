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


class PartOfSpeech(str, Enum):
    rzeczownik = "rzeczownik"
    czasownik = "czasownik"
    przymiotnik = "przymiotnik"
    zaimek = "zaimek"
    przyslowek = "przysłówek"
    inne = "inne"


class GrammaticalCase(str, Enum):
    mianownik = "mianownik"
    dopelniacz = "dopełniacz"
    celownik = "celownik"
    biernik = "biernik"
    narzednik = "narzędnik"
    miejscownik = "miejscownik"
    wolacz = "wołacz"


class GrammaticalGender(str, Enum):
    meskoosobowy = "męskoosobowy"      # masculine personal (virile)
    meskozywotny = "męskozywotny"      # masculine animate (non-personal)
    meskorzeczowy = "męskorzeczowy"    # masculine inanimate
    zenski = "żeński"
    nijaki = "nijaki"


def is_virile(gender) -> bool:
    """True only for męskoosobowy — the gender that drives virile PLURAL
    agreement and the accusative-PLURAL=genitive-plural rule (B1).

    NOTE: this is a plural-only distinction. It does NOT govern the accusative
    SINGULAR, which follows animacy: both męskoosobowy AND męskozywotny take
    Acc.Sg = Gen.Sg (kota, psa). Use is_animate_masculine() for singular."""
    if gender is None:
        return False
    value = gender.value if isinstance(gender, GrammaticalGender) else str(gender)
    return value == GrammaticalGender.meskoosobowy.value


def is_animate_masculine(gender) -> bool:
    """True for męskoosobowy and męskozywotny — the genders whose accusative
    SINGULAR equals the genitive singular (widzę kota/studenta, not *kot)."""
    if gender is None:
        return False
    value = gender.value if isinstance(gender, GrammaticalGender) else str(gender)
    return value in {
        GrammaticalGender.meskoosobowy.value,
        GrammaticalGender.meskozywotny.value,
    }


class GrammaticalNumber(str, Enum):
    singular = "singular"
    plural = "plural"


class VerbTense(str, Enum):
    terazniejszy = "teraźniejszy"
    przeszly = "przeszły"
    przyszly = "przyszły"


class Aspect(str, Enum):
    dokonany = "dokonany"        # perfective
    niedokonany = "niedokonany"  # imperfective


class Pronoun(str, Enum):
    ja = "ja"
    ty = "ty"
    on_ona_ono = "on/ona/ono"
    my = "my"
    wy = "wy"
    oni = "oni"   # męskoosobowy (virile) plural — "oni robili"
    one = "one"   # niemęskoosobowy (non-virile) plural — "one robiły"


# ── Core tables ──────────────────────────────────────────────


class Word(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    polish: str = Field(index=True)
    english: str
    ukrainian: str
    part_of_speech: PartOfSpeech = Field(default=PartOfSpeech.inne, index=True)
    gender: Optional[str] = Field(default=None)  # for nouns: męski/żeński/nijaki
    aspect: Optional[Aspect] = Field(default=None)  # for czasownik only (M4/M5)


class WordOption(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("word_id", "language", "value"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    word_id: int = Field(foreign_key="word.id")
    language: WordLanguage
    value: str = Field(index=True)


# ── Declension / Conjugation forms ──────────────────────────


class WordDeclension(SQLModel, table=True):
    """Declined forms for rzeczownik/przymiotnik (cases x genders x numbers)."""
    __table_args__ = (
        UniqueConstraint("word_id", "case", "gender", "number"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    word_id: int = Field(foreign_key="word.id")
    case: GrammaticalCase
    gender: GrammaticalGender
    number: GrammaticalNumber
    form: str


class VerbConjugation(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("word_id", "pronoun", "tense"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    word_id: int = Field(foreign_key="word.id")
    pronoun: Pronoun
    tense: VerbTense = Field(default=VerbTense.terazniejszy)
    conjugated_form: str


# ── Practice sentences ───────────────────────────────────────


class PracticeSentence(SQLModel, table=True):
    """Pre-generated sentences for endings practice."""
    id: Optional[int] = Field(default=None, primary_key=True)
    word_id: int = Field(foreign_key="word.id", index=True)
    part_of_speech: PartOfSpeech
    sentence: str  # with ___ placeholder
    correct_answer: str
    case: Optional[str] = Field(default=None)
    gender: Optional[str] = Field(default=None)
    number: Optional[str] = Field(default=None)
    pronoun: Optional[str] = Field(default=None)
    tense: Optional[str] = Field(default=None)


# ── Session ──────────────────────────────────────────────────


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


# ── Practice records ─────────────────────────────────────────


class AttemptKind(str, Enum):
    practice = "practice"   # translation / writing / pronunciation
    endings = "endings"     # grammar endings practice


class Attempt(SQLModel, table=True):
    """Single source of truth for one graded answer (M3). Supersedes the
    disjoint PracticeRecord + EndingsPracticeRecord tables."""
    id: Optional[int] = Field(default=None, primary_key=True)
    word_id: int = Field(foreign_key="word.id", index=True)
    kind: AttemptKind = Field(index=True)
    language_set: Optional[LanguageSet] = Field(default=None)
    direction: Optional[PracticeDirection] = Field(default=None)
    part_of_speech: Optional[PartOfSpeech] = Field(default=None)
    was_correct: bool
    user_answer: Optional[str] = Field(default=None)
    correct_answer: Optional[str] = Field(default=None)
    practice_date: date = Field(default_factory=date.today, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── Admin ────────────────────────────────────────────────────


class AppSetting(SQLModel, table=True):
    key: str = Field(primary_key=True)
    value: str


class ConnectedDevice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ip_address: str = Field(index=True)
    user_agent: str
    device_type: str
    browser: str
    os: str
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    request_count: int = Field(default=1)
