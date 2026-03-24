from sqlmodel import Session, SQLModel, create_engine, select

from app.models import AppSetting, UserSession, Word
from app.seed import seed_words

DATABASE_URL = "sqlite:////app/data/polingo.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


def _migrate_add_columns(engine) -> None:
    """Add new nullable columns to existing tables if missing."""
    import sqlite3
    url = str(engine.url).replace("sqlite:///", "")
    try:
        conn = sqlite3.connect(url)
        cursor = conn.cursor()
        for table, column in [
            ("practicerecord", "user_answer"),
            ("practicerecord", "correct_answer"),
            ("endingspracticerecord", "user_answer"),
            ("endingspracticerecord", "correct_answer"),
        ]:
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT")
            except sqlite3.OperationalError:
                pass  # column already exists
        conn.commit()
        conn.close()
    except Exception:
        pass  # DB doesn't exist yet, create_all will handle it


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
