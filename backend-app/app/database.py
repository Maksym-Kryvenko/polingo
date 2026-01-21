from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Word
from app.seed import seed_words


DATABASE_URL = "sqlite:///polingo.db"

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


def get_session() -> Session:
    return Session(engine)
