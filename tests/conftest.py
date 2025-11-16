# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

# Importa tu app y dependencias
from app.main import app
from app.database import get_session
# Importa TODOS tus modelos aquí para que SQLModel los registre
from app.models import User, PokedexEntry, Team, TeamPokemon

# --- Configuración de la Base de Datos de Testing ---
# Esta será la ÚNICA fuente de verdad para el motor de tests

DATABASE_URL_TEST = "sqlite:///:memory:"

engine = create_engine(
    DATABASE_URL_TEST,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


# --- Override de la Sesión de DB ---

def override_get_session():
    """Reemplaza la sesión de producción por la sesión en memoria."""
    with Session(engine) as session:
        yield session


# Aplicamos el override a la app UNA SOLA VEZ
app.dependency_overrides[get_session] = override_get_session

from app.routers import auth as auth_router_utils
from app.routers import pokemon, pokedex
from app import auth as app_auth_utils  # Este es el segundo archivo auth.py


@pytest.fixture(autouse=True)
def clear_rate_limiters():
    """Limpia todos los diccionarios de rate limit antes de cada test."""
    app_auth_utils.LOGIN_LIMIT.clear()
    app_auth_utils.REGISTER_LIMIT.clear()

    # Limpia los diccionarios de rate limit de los routers
    pokemon.SEARCH_LIMIT.clear()
    pokemon.DETAIL_LIMIT.clear()
    pokemon.CARD_LIMIT.clear()
    pokedex.POKEDEX_LIMIT.clear()


# --- Fixture de Cliente Compartida ---

@pytest.fixture(name="client")
def client_fixture():
    """
    Fixture principal que prepara la app y la base de datos para un test.
    Se ejecutará una vez por cada test que lo pida.
    """
    # Se asegura que todos los modelos importados (User, PokedexEntry, etc.)
    # se creen en la base de datos en memoria.
    SQLModel.metadata.create_all(engine)

    # Proporciona el TestClient
    with TestClient(app) as client:
        yield client

    # Limpia (borra todas las tablas) la DB después de cada test
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="session")
def session_fixture(client: TestClient):
    """
    Proporciona una sesión de base de datos de prueba.

    Depende de 'client' para asegurarse de que las tablas se creen
    antes de que la sesión se use y se borren después.
    """
    # El client_fixture ya ha ejecutado SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    # El client_fixture se encargará de SQLModel.metadata.drop_all(engine) después