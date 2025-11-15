# tests/test_auth.py
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session  # Necesario para los type hints (ej: session: Session)

from app.models import User
from app.auth import get_password_hash


# --- Fixture Específica de Auth ---

@pytest.fixture(name="test_user")
def test_user_fixture(session: Session):  # <-- Pide la fixture 'session'
    """
    Crea un usuario directamente en la base de datos para tests de login.
    """
    # 'session' ahora es una sesión real y funcional de conftest.py
    hashed_password = get_password_hash("ValidPass123")
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=hashed_password
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


# --- Tests de Registro ---

def test_register_user_success(client: TestClient, session: Session):  # <-- Pide la fixture 'session'
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "StrongPassword123"
        }
    )
    data = response.json()
    assert response.status_code == 200
    assert data["message"] == "Usuario registrado correctamente"
    assert "user_id" in data

    # Usa la 'session' directamente
    user = session.get(User, data["user_id"])
    assert user is not None
    assert user.username == "newuser"


def test_register_user_already_exists(client: TestClient, test_user: User):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "another@example.com",
            "password": "StrongPassword123"
        }
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "El usuario o email ya existen."


def test_register_email_already_exists(client: TestClient, test_user: User):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "anotheruser",
            "email": "test@example.com",
            "password": "StrongPassword123"
        }
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "El usuario o email ya existen."


def test_register_invalid_email(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "emailuser",
            "email": "not-an-email",
            "password": "StrongPassword123"
        }
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Email inválido."


def test_register_weak_password(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "weakpass",
            "email": "weak@example.com",
            "password": "weak"
        }
    )
    assert response.status_code == 400
    assert "Contraseña insegura" in response.json()["detail"]


# --- Tests de Login ---

def test_login_success(client: TestClient, test_user: User):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "ValidPass123"
        }
    )
    data = response.json()
    assert response.status_code == 200
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_username(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "nonexistent",
            "password": "ValidPass123"
        }
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciales inválidas"


def test_login_invalid_password(client: TestClient, test_user: User):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "WrongPassword"
        }
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciales inválidas"


# --- Test de Dependencia ---

def test_protected_route_success(client: TestClient, test_user: User):
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "ValidPass123"}
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/pokedex/", headers=headers)

    assert response.status_code == 200
    assert response.json() == []


def test_protected_route_invalid_token(client: TestClient):
    headers = {"Authorization": "Bearer FAKE-TOKEN"}
    response = client.get("/api/v1/pokedex/", headers=headers)

    assert response.status_code == 401
    assert "inválido" in response.json()["detail"]


def test_protected_route_no_token(client: TestClient):
    response = client.get("/api/v1/pokedex/")

    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"