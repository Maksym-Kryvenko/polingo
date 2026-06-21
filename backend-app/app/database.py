import logging
from pathlib import Path

from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import inspect
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app import config
from app.models import AppSetting, UserSession, Word
from app.seed import seed_words

logger = logging.getLogger("polingo.database")

_MEMORY_URLS = {"sqlite://", "sqlite:///:memory:"}
_ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"


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


def _alembic_config() -> AlembicConfig:
    cfg = AlembicConfig(str(_ALEMBIC_INI))
    cfg.set_main_option("script_location", str(_ALEMBIC_INI.parent / "migrations"))
    cfg.set_main_option("sqlalchemy.url", config.database_url())
    return cfg


def run_migrations() -> None:
    """Bring the schema to head. In-memory DBs (tests) are built directly from
    model metadata — Alembic is exercised against a file DB in test_migrations.
    Pre-Alembic file DBs (built by the old create_all path) are stamped at the
    baseline before upgrading so their existing data is preserved."""
    url = config.database_url()
    if url in _MEMORY_URLS:
        SQLModel.metadata.create_all(engine)
        return
    cfg = _alembic_config()
    # Inspect the same physical DB Alembic will target (build a throwaway engine
    # from the resolved URL rather than reusing the module engine).
    insp_engine = create_engine(url)
    try:
        tables = set(inspect(insp_engine).get_table_names())
    finally:
        insp_engine.dispose()
    if "alembic_version" not in tables and "word" in tables:
        command.stamp(cfg, "0001_baseline")
    command.upgrade(cfg, "head")


def init_db() -> None:
    run_migrations()
    with Session(engine) as session:
        has_words = session.exec(select(Word)).first()
        if not has_words:
            seed_words(session)
        has_session = session.exec(select(UserSession)).first()
        if not has_session:
            session.add(UserSession())
            session.commit()
        if not session.get(AppSetting, "generate_on_the_fly"):
            session.add(AppSetting(key="generate_on_the_fly", value="false"))
            session.commit()
        if not session.get(AppSetting, "tts_source"):
            session.add(AppSetting(key="tts_source", value="browser"))
            session.commit()


def get_session() -> Session:
    return Session(engine)
