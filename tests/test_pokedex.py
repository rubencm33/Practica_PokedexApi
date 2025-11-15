# tests/test_pokedex.py
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session  # Necesario para los type hints
from unittest.mock import MagicMock
from fastapi import HTTPException

# Importa modelos y servicios
from app.models import User, PokedexEntry
from app.auth import get_password_hash


# No necesitamos PokeAPIService aquí, solo mockear la ruta

# --- Fixtures Específicas de Pokedex ---

@pytest.fixture(name="test_user")
def test_user_fixture(session: Session):  # <-- Pide la fixture 'session'
    """Crea un usuario en la DB para los tests."""
    hashed_password = get_password_hash("ValidPass123")
    user = User(
        username="pokedex_user",
        email="pokedex@example.com",
        hashed_password=hashed_password
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(client: TestClient, test_user: User):
    """Inicia sesión y devuelve los headers de autorización."""
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "pokedex_user", "password": "ValidPass123"}
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(name="mock_pokeapi")
def mock_pokeapi_fixture(mocker):
    """
    Mockea el pokeapi_service usado en pokedex.py.
    """
    mock_pokemon_data = {
        "id": 1,
        "name": "bulbasaur",
        "sprites": {"front_default": "http://example.com/bulbasaur.png"},
        "types": [{"type": {"name": "grass"}}]
    }
    mock_get = MagicMock(return_value=mock_pokemon_data)

    # Ruta corregida al servicio dentro del módulo del router
    mocker.patch('app.routers.pokedex.pokeapi_service.get_pokemon', mock_get)

    return mock_get


@pytest.fixture(name="test_pokedex_entry")
def test_pokedex_entry_fixture(session: Session, test_user: User):  # <-- Pide 'session'
    """Crea una entrada de Pokédex directamente en la DB."""
    entry = PokedexEntry(
        pokemon_id=25,
        pokemon_name="pikachu",
        pokemon_sprite="http://example.com/pikachu.png",
        is_captured=True,
        favorite=False,
        owner_id=test_user.id
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


# --- Tests para Endpoints de Pokedex ---

def test_add_pokemon_to_pokedex(client: TestClient, auth_headers: dict, mock_pokeapi: MagicMock,
                                session: Session):  # <-- Pide 'session'
    """
    Test para añadir un nuevo Pokémon a la Pokédex (POST /).
    """
    entry_data = {
        "pokemon_id": 1,
        "nickname": "Bulby",
        "is_captured": False
    }
    response = client.post("/api/v1/pokedex/", json=entry_data, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["pokemon_id"] == 1
    assert data["nickname"] == "Bulby"

    mock_pokeapi.assert_called_with(1)

    # Corregí el .get() para usar el ID de la respuesta
    entry = session.get(PokedexEntry, data["id"])
    assert entry is not None
    assert entry.pokemon_name == "bulbasaur"
    assert entry.nickname == "Bulby"


def test_add_pokemon_pokeapi_fails(client: TestClient, auth_headers: dict, mocker):
    """
    Test de qué pasa si PokeAPI falla al añadir un Pokémon.
    """
    # Ruta corregida
    mocker.patch(
        'app.routers.pokedex.pokeapi_service.get_pokemon',
        MagicMock(side_effect=HTTPException(status_code=404, detail="Not Found"))
    )

    entry_data = {"pokemon_id": 999, "is_captured": False}
    response = client.post("/api/v1/pokedex/", json=entry_data, headers=auth_headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Not Found"


def test_list_pokedex(client: TestClient, auth_headers: dict, test_pokedex_entry: PokedexEntry):
    response = client.get("/api/v1/pokedex/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["pokemon_id"] == 25


def test_list_pokedex_filtered(client: TestClient, auth_headers: dict, test_pokedex_entry: PokedexEntry):
    response_captured = client.get("/api/v1/pokedex/?captured=true", headers=auth_headers)
    assert response_captured.status_code == 200
    assert len(response_captured.json()) == 1

    response_not_captured = client.get("/api/v1/pokedex/?captured=false", headers=auth_headers)
    assert response_not_captured.status_code == 200
    assert len(response_not_captured.json()) == 0


def test_update_pokedex_entry(client: TestClient, auth_headers: dict, test_pokedex_entry: PokedexEntry,
                              session: Session):  # <-- Pide 'session'
    update_data = {
        "nickname": "Sparky",
        "favorite": True
    }
    # NO pongas el expire aquí
    entry_id = test_pokedex_entry.id
    response = client.patch(f"/api/v1/pokedex/{entry_id}", json=update_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["nickname"] == "Sparky"
    assert data["favorite"] == True

    # --- AÑADE ESTA LÍNEA AQUÍ ---
    # Le dice a la sesión del test que "olvide" la versión en caché
    # que tiene de este objeto, porque sabe que la API la ha cambiado.
    session.expire(test_pokedex_entry)
    # --------------------------------

    # Ahora, session.get() irá a la BBDD a buscar la nueva versión
    entry = session.get(PokedexEntry, entry_id)
    assert entry.nickname == "Sparky"
    assert entry.favorite == True


def test_update_pokedex_entry_not_owner(client: TestClient, test_pokedex_entry: PokedexEntry,
                                        session: Session):  # <-- Pide 'session'
    # 1. Creamos un "otro_usuario"
    hashed_password = get_password_hash("OtherPass123")
    other_user = User(username="other", email="other@e.com", hashed_password=hashed_password)
    session.add(other_user)
    session.commit()

    # 2. Iniciamos sesión como "otro_usuario"
    login_res = client.post("/api/v1/auth/login", json={"username": "other", "password": "OtherPass123"})
    other_headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

    # 3. "otro_usuario" intenta editar la entrada
    update_data = {"nickname": "HACKED"}
    entry_id = test_pokedex_entry.id
    response = client.patch(f"/api/v1/pokedex/{entry_id}", json=update_data, headers=other_headers)

    assert response.status_code == 403
    assert "No puedes modificar esta entrada" in response.json()["detail"]


def test_delete_pokedex_entry(client: TestClient, auth_headers: dict, test_pokedex_entry: PokedexEntry,
                              session: Session):  # <-- Pide 'session'
    entry_id = test_pokedex_entry.id
    response = client.delete(f"/api/v1/pokedex/{entry_id}", headers=auth_headers)

    assert response.status_code == 204
    session.expire(test_pokedex_entry)

    entry = session.get(PokedexEntry, entry_id)
    assert entry is None


def test_export_pokedex_csv(client: TestClient, auth_headers: dict, test_pokedex_entry: PokedexEntry):
    response = client.get("/api/v1/pokedex/export?format=csv", headers=auth_headers)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")

    content = response.text
    assert "pokemon_id,pokemon_name,nickname,is_captured,favorite" in content
    assert "25,pikachu" in content


def test_get_pokedex_stats(client: TestClient, auth_headers: dict, test_pokedex_entry: PokedexEntry, mocker):
    # Ruta corregida
    mocker.patch(
        'app.routers.pokedex.pokeapi_service.get_pokemon',
        MagicMock(return_value={
            "id": 25, "name": "pikachu",
            "types": [{"type": {"name": "electric"}}]
        })
    )

    response = client.get("/api/v1/pokedex/stats", headers=auth_headers)

    assert response.status_code == 200
    stats = response.json()
    assert stats["total_pokemon"] == 1
    assert stats["captured"] == 1
    assert stats["most_common_type"] == "electric"