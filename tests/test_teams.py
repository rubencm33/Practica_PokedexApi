import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import User, PokedexEntry, Team, TeamPokemon
from app.auth import get_password_hash


# --- Fixtures Específicas de Teams ---

@pytest.fixture(name="test_user")
def test_user_fixture(session: Session):
    """Crea un usuario 'team_user' para estos tests."""
    hashed_password = get_password_hash("ValidPass123")
    user = User(
        username="team_user",
        email="team_user@example.com",
        hashed_password=hashed_password
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(client: TestClient, test_user: User):
    """Inicia sesión como 'team_user' y devuelve los headers."""
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "team_user", "password": "ValidPass123"}
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(name="user_pokedex_entries")
def user_pokedex_entries_fixture(session: Session, test_user: User):
    """
    Añade Pokémon (IDs 1, 4, 7) a la Pokédex del 'test_user'.
    """
    entry1 = PokedexEntry(
        pokemon_id=1, pokemon_name="bulbasaur", pokemon_sprite="url1", owner_id=test_user.id
    )
    entry2 = PokedexEntry(
        pokemon_id=4, pokemon_name="charmander", pokemon_sprite="url4", owner_id=test_user.id
    )
    entry3 = PokedexEntry(
        pokemon_id=7, pokemon_name="squirtle", pokemon_sprite="url7", owner_id=test_user.id
    )
    session.add_all([entry1, entry2, entry3])
    session.commit()
    return [entry1, entry2, entry3]


@pytest.fixture(name="test_team")
def test_team_fixture(session: Session, user_pokedex_entries: list):
    """
    Crea un equipo para 'test_user' con Pokémon 1 y 4.
    """
    user_id = user_pokedex_entries[0].owner_id
    team = Team(name="Team Rocket", owner_id=user_id)
    session.add(team)
    session.commit()
    session.refresh(team)

    tp1 = TeamPokemon(team_id=team.id, pokemon_id=1)
    tp2 = TeamPokemon(team_id=team.id, pokemon_id=4)
    session.add_all([tp1, tp2])
    session.commit()

    session.refresh(team)  # Refresca para cargar la relación 'team_pokemon'
    return team


# --- Tests para Endpoints de Teams ---

def test_create_team_success(client: TestClient, auth_headers: dict, user_pokedex_entries: list, session: Session):
    """
    Test para crear un equipo exitosamente (POST /).
    El usuario tiene Pokémon 1, 4, 7.
    """
    team_data = {
        "name": "Team Victory",
        "description": "Winning team",
        "pokemon_ids": [1, 7]  # IDs que el usuario sí tiene
    }
    response = client.post("/api/v1/teams/", json=team_data, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["message"] == "Equipo creado correctamente"
    assert data["team_name"] == "Team Victory"

    # Verifica en la DB
    team = session.get(Team, data["team_id"])
    assert team is not None
    assert len(team.team_pokemon) == 2
    assert team.pokemon_ids == [1, 7]  # Comprueba la propiedad


def test_create_team_pokemon_not_in_pokedex(client: TestClient, auth_headers: dict, user_pokedex_entries: list):
    """
    Test de error al crear un equipo con Pokémon que no están en la Pokédex (POST /).
    """
    team_data = {
        "name": "Team Invalid",
        "pokemon_ids": [1, 999]  # 999 no está en la Pokédex
    }
    response = client.post("/api/v1/teams/", json=team_data, headers=auth_headers)

    assert response.status_code == 400
    assert "no están en tu Pokédex: [999]" in response.json()["detail"]


def test_create_team_too_many_pokemon(client: TestClient, auth_headers: dict, user_pokedex_entries: list):
    """
    Test de error al crear un equipo con más de 6 Pokémon (POST /).
    """
    team_data = {
        "name": "Team Full",
        "pokemon_ids": [1, 4, 7, 1, 4, 7, 1]  # 7 Pokémon
    }
    response = client.post("/api/v1/teams/", json=team_data, headers=auth_headers)

    assert response.status_code == 400
    assert "no puede tener más de 6 Pokémon" in response.json()["detail"]


def test_list_teams(client: TestClient, auth_headers: dict, test_team: Team):
    """
    Test para listar los equipos del usuario (GET /).
    La fixture 'test_team' ha creado 1 equipo.
    """
    response = client.get("/api/v1/teams/", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["name"] == "Team Rocket"
    assert data[0]["pokemon_ids"] == [1, 4]


def test_update_team_success(client: TestClient, auth_headers: dict, test_team: Team, session: Session):
    """
    Test para actualizar un equipo (PUT /{team_id}).
    'test_team' tiene [1, 4]. 'user_pokedex_entries' tiene [1, 4, 7].
    """
    update_data = {
        "name": "Team Updated",
        "pokemon_ids": [1, 7]  # Cambiamos 4 por 7
    }
    team_id = test_team.id
    response = client.put(f"/api/v1/teams/{team_id}", json=update_data, headers=auth_headers)

    assert response.status_code == 200

    # Verifica en la DB
    session.expire(test_team)  # Forzar recarga desde la DB
    updated_team = session.get(Team, team_id)
    assert updated_team.name == "Team Updated"
    assert updated_team.pokemon_ids == [1, 7]


def test_update_team_not_owned(client: TestClient, test_team: Team, session: Session):
    """
    Test de error al intentar actualizar un equipo de otro usuario (PUT /{team_id}).
    """
    # 1. Crea un "otro_usuario"
    hashed_password = get_password_hash("OtherPass123")
    other_user = User(username="other", email="other@e.com", hashed_password=hashed_password)
    session.add(other_user)
    session.commit()

    # 2. Inicia sesión como "otro_usuario"
    login_res = client.post("/api/v1/auth/login", json={"username": "other", "password": "OtherPass123"})
    other_headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

    # 3. "otro_usuario" intenta editar el 'test_team' (de 'test_user')
    update_data = {"name": "HACKED"}
    team_id = test_team.id
    response = client.put(f"/api/v1/teams/{team_id}", json=update_data, headers=other_headers)

    assert response.status_code == 404
    assert "Team not found" in response.json()["detail"]


def test_update_team_add_pokemon_not_in_pokedex(client: TestClient, auth_headers: dict, test_team: Team):
    """
    Test de error al actualizar un equipo con un Pokémon que no se tiene (PUT /{team_id}).
    """
    update_data = {
        "pokemon_ids": [1, 999]  # 999 no está en la Pokédex
    }
    team_id = test_team.id
    response = client.put(f"/api/v1/teams/{team_id}", json=update_data, headers=auth_headers)

    assert response.status_code == 400
    assert "User does not own Pokémon 999" in response.json()["detail"]


def test_export_team_pdf(client: TestClient, auth_headers: dict, test_team: Team):
    """
    Test para exportar un equipo a PDF (GET /{team_id}/export).
    """
    team_id = test_team.id
    response = client.get(f"/api/v1/teams/{team_id}/export", headers=auth_headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment; filename=team_1.pdf" in response.headers["content-disposition"]

    # Verifica que el contenido es un PDF (los PDF empiezan con %PDF-)
    assert response.content.startswith(b'%PDF-')