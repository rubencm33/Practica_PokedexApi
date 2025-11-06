from sqlmodel import SQLModel, Session, create_engine
from app.config import settings

# Usa la variable de entorno DATABASE_URL o una por defecto
DATABASE_URL = getattr(settings, "DATABASE_URL", "sqlite:///./pokedex.db")

# Crear el motor de base de datos
engine = create_engine(DATABASE_URL, echo=False)


def get_session():
    """
    Dependencia de FastAPI para obtener una sesión de base de datos.
    Se usa con Depends(get_session) en los endpoints.
    """
    with Session(engine) as session:
        yield session


def init_db():
    """
    Crea todas las tablas en la base de datos (si no existen).
    """
    import app.models  # asegura que los modelos están importados
    SQLModel.metadata.create_all(engine)

