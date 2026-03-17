from sqlmodel import Session, SQLModel, create_engine, select

from app.models import AppSetting, UserSession, Word
from app.seed import seed_words

DATABASE_URL = "sqlite:////app/data/polingo.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
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


def get_session() -> Session:
    return Session(engine)
