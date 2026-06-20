import logging
import sqlite3

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app import config
from app.models import AppSetting, UserSession, Word
from app.seed import seed_words

logger = logging.getLogger("polingo.database")

_MEMORY_URLS = {"sqlite://", "sqlite:///:memory:"}


def make_engine(url: str):
    """Create an engine. In-memory DBs need StaticPool so every connection
    shares one database; file DBs get a 30s busy timeout to avoid 'database
    is locked' under concurrent writes (M9)."""
    if url in _MEMORY_URLS:
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_engine(
        url,
        connect_args={"check_same_thread": False, "timeout": 30},
    )


engine = make_engine(config.database_url())


def _migrate_add_columns(engine) -> None:
    """Add new nullable columns to existing tables if missing. Swallows ONLY
    the 'duplicate column' case; every other failure is logged and re-raised
    so a broken migration cannot start the app silently (B3)."""
    db_path = engine.url.database
    if db_path in (None, ":memory:"):
        return  # in-memory DB: create_all already built the current schema
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        for table, column in [
            ("practicerecord", "user_answer"),
            ("practicerecord", "correct_answer"),
            ("endingspracticerecord", "user_answer"),
            ("endingspracticerecord", "correct_answer"),
        ]:
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT")
            except sqlite3.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    logger.error("Migration failed on %s.%s: %s", table, column, exc)
                    raise
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    _migrate_add_columns(engine)
    with Session(engine) as session:
        has_words = session.exec(select(Word)).first()
        if not has_words:
            seed_words(session)
        has_session = session.exec(select(UserSession)).first()
        if not has_session:
            session.add(UserSession())
            session.commit()
        # Ensure default app settings
        if not session.get(AppSetting, "generate_on_the_fly"):
            session.add(AppSetting(key="generate_on_the_fly", value="false"))
            session.commit()
        if not session.get(AppSetting, "tts_source"):
            session.add(AppSetting(key="tts_source", value="browser"))
            session.commit()


def get_session() -> Session:
    return Session(engine)
