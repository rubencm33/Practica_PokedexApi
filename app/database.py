from sqlmodel import SQLModel, Session, create_engine
from app.config import settings

DATABASE_URL = getattr(settings, "DATABASE_URL", "sqlite:///./pokedex.db")

engine = create_engine(DATABASE_URL, echo=False)


def get_session():
    with Session(engine) as session:
        yield session


def init_db():
    import app.models
    SQLModel.metadata.create_all(engine)

