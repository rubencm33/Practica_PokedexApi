import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from unittest.mock import MagicMock, patch
from reportlab.lib.pagesizes import letter
from app.models import User
from app.auth import get_password_hash


@pytest.fixture(name="test_user")
def test_user_fixture(session: Session):
    """Crea un usuario 'pokemon_user' para estos tests."""
    hashed_password = get_password_hash("ValidPass123")
    user = User(
        username="pokemon_user",
        email="pokemon_user@example.com",
        hashed_password=hashed_password
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(client: TestClient, test_user: User):
    """Inicia sesión como 'pokemon_user' y devuelve los headers."""
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "pokemon_user", "password": "ValidPass123"}
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(name="mock_pikachu_data")
def mock_pikachu_data_fixture():
    """Mock de datos simplificados para Pikachu."""
    return {
        "id": 25,
        "name": "pikachu",
        "sprites": {
            "front_default": "http://example.com/pikachu.png",
            "other": {
                "official-artwork": {
                    "front_default": "http://example.com/pikachu-official.png"
                }
            }
        },
        "types": [{"type": {"name": "electric"}}],
        "abilities": [{"ability": {"name": "static"}}],
        "stats": [{"stat": {"name": "hp"}, "base_stat": 35}]
    }


@pytest.fixture(name="mock_bulbasaur_data")
def mock_bulbasaur_data_fixture():
    """Mock de datos simplificados para Bulbasaur."""
    return {
        "id": 1,
        "name": "bulbasaur",
        "sprites": {"front_default": "http://example.com/bulbasaur.png"},
        "types": [{"type": {"name": "grass"}}]
    }


@pytest.fixture(name="mock_species_data")
def mock_species_data_fixture():
    """Mock de datos de especie (para descripción)."""
    return {
        "flavor_text_entries": [
            {"flavor_text": "Not in spanish.", "language": {"name": "en"}},
            {"flavor_text": "Una descripción en español.", "language": {"name": "es"}}
        ]
    }


def test_search_pokemon(client: TestClient, auth_headers: dict, mock_bulbasaur_data: dict, mocker):
    """
    Test para buscar Pokémon (GET /search).
    """
    mocker.patch(
        'app.routers.pokemon.pokeapi_service.search_pokemon',
        return_value={"results": [{"name": "bulbasaur"}]}
    )
    mock_get_pokemon = mocker.patch(
        'app.routers.pokemon.pokeapi_service.get_pokemon',
        return_value=mock_bulbasaur_data
    )

    response = client.get("/api/v1/pokemon/search", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "bulbasaur"
    assert data[0]["types"] == ["grass"]
    mock_get_pokemon.assert_called_with("bulbasaur")


def test_search_pokemon_with_name_filter(client: TestClient, auth_headers: dict, mock_pikachu_data: dict,
                                         mock_bulbasaur_data: dict, mocker):
    """
    Test para filtrar la búsqueda por nombre (GET /search?name=pika).
    """
    mocker.patch(
        'app.routers.pokemon.pokeapi_service.search_pokemon',
        return_value={"results": [{"name": "bulbasaur"}, {"name": "pikachu"}]}
    )

    def get_pokemon_side_effect(name_or_id):
        if name_or_id == "bulbasaur":
            return mock_bulbasaur_data
        if name_or_id == "pikachu":
            return mock_pikachu_data
        return None

    mock_get_pokemon = mocker.patch(
        'app.routers.pokemon.pokeapi_service.get_pokemon',
        side_effect=get_pokemon_side_effect
    )
    # -----------------------------------

    response = client.get("/api/v1/pokemon/search?name=pika", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    assert data[0]["name"] == "pikachu"  # Esto ahora funcionará

    mock_get_pokemon.assert_called_once_with("pikachu")


def test_search_pokemon_no_results(client: TestClient, auth_headers: dict, mock_bulbasaur_data: dict, mocker):
    """
    Test para una búsqueda filtrada que no devuelve resultados (GET /search?name=xyz).
    """
    mocker.patch(
        'app.routers.pokemon.pokeapi_service.search_pokemon',
        return_value={"results": [{"name": "bulbasaur"}]}
    )
    mocker.patch(
        'app.routers.pokemon.pokeapi_service.get_pokemon',
        return_value=mock_bulbasaur_data
    )

    response = client.get("/api/v1/pokemon/search?name=xyz", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {"message": "No se encontraron Pokémon con ese nombre"}


def test_get_pokemon_details(client: TestClient, auth_headers: dict, mock_pikachu_data: dict, mocker):
    """
    Test para obtener los detalles de un Pokémon (GET /{id_or_name}).
    """
    mock_get = mocker.patch(
        'app.routers.pokemon.pokeapi_service.get_pokemon',
        return_value=mock_pikachu_data
    )

    response = client.get("/api/v1/pokemon/pikachu", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 25
    assert data["name"] == "pikachu"
    assert data["abilities"] == ["static"]
    assert data["stats"] == {"hp": 35}
    mock_get.assert_called_with("pikachu")


def test_get_pokemon_details_api_error(client: TestClient, auth_headers: dict, mocker):
    """
    Test de error 500 si la API de Pokémon falla (GET /{id_or_name}).
    """
    mocker.patch(
        'app.routers.pokemon.pokeapi_service.get_pokemon',
        side_effect=Exception("PokeAPI is down")
    )

    response = client.get("/api/v1/pokemon/pikachu", headers=auth_headers)

    assert response.status_code == 500
    assert "Error al obtener detalles: PokeAPI is down" in response.json()["detail"]


def test_generate_pokemon_card(client: TestClient, auth_headers: dict, mock_pikachu_data: dict, mock_species_data: dict,
                               mocker):
    """
    Test para generar la tarjeta PDF de un Pokémon (GET /{id_or_name}/card).
    Aquí mockeamos todo el proceso de creación de archivos.
    """
    mocker.patch(
        'app.routers.pokemon.pokeapi_service.get_pokemon',
        return_value=mock_pikachu_data
    )
    mocker.patch(
        'app.routers.pokemon.pokeapi_service.get_pokemon_species',
        return_value=mock_species_data
    )

    mock_makedirs = mocker.patch('app.routers.pokemon.os.makedirs')
    mock_urlretrieve = mocker.patch('app.routers.pokemon.request.urlretrieve')
    mock_path_exists = mocker.patch('app.routers.pokemon.os.path.exists', return_value=True)

    mock_canvas = mocker.patch('app.routers.pokemon.canvas.Canvas')

    with patch('app.routers.pokemon.FileResponse') as mock_file_response:
        # Asignamos una respuesta genérica para que el test funcione
        mock_file_response.return_value = MagicMock(status_code=200)

        response = client.get("/api/v1/pokemon/25/card", headers=auth_headers)

        assert response.status_code == 200

        mock_makedirs.assert_called_with("app/exports", exist_ok=True)

        mock_urlretrieve.assert_called_with(
            "http://example.com/pikachu-official.png",
            mocker.ANY
        )

        mock_canvas.assert_called_with(
            mocker.ANY,
            pagesize=letter
        )

        mock_file_response.assert_called_with(
            mocker.ANY,
            filename="pikachu_card.pdf",
            media_type="application/pdf"
        )