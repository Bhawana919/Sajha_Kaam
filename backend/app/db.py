from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app import models  # noqa: F401  (registers tables)
from app.config import settings

engine = create_engine(settings().database_url, connect_args={"check_same_thread": False})


def init_db(reset: bool = False) -> None:
    if reset:
        SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
