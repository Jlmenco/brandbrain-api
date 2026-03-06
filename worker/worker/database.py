from sqlmodel import Session, create_engine

from worker.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)


def get_session() -> Session:
    """Returns a new Session (caller must close/use as context manager)."""
    return Session(engine)
