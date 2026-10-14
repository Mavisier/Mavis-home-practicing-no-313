from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    get_settings().database_url,
    pool_pre_ping=True,
    pool_size=get_settings().database_pool_size,
    max_overflow=0,
    pool_timeout=10,
    # Keep protocol state simple for the optional multiplexed PGlite helper.
    connect_args={"connect_timeout": 5, "prepare_threshold": None},
)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
