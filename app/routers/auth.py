# app/routers/auth.py
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from app.database import get_session
from app.models import User, UserCreate
from app import auth

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


# -----------------------------
# Registro de usuarios
# -----------------------------
@router.post("/register")
def register_user(
    request: Request,
    user_data: UserCreate,
    session: Session = Depends(get_session)
):
    ip = request.client.host

    # Rate limit: 5 registros/hora/IP
    if auth.rate_limited(ip, auth.REGISTER_LIMIT, 5, 3600):
        raise HTTPException(status_code=429, detail="Demasiados registros desde esta IP. Intenta más tarde.")

    if not auth.verify_email(user_data.email):
        raise HTTPException(status_code=400, detail="Email inválido.")

    if not auth.verify_password_strength(user_data.password):
        raise HTTPException(
            status_code=400,
            detail="Contraseña insegura. Debe tener 8 caracteres, 1 mayúscula y 1 número."
        )

    # Verificar si ya existe el usuario o email
    statement = select(User).where(
        (User.username == user_data.username) | (User.email == user_data.email)
    )
    if session.exec(statement).first():
        raise HTTPException(status_code=400, detail="El usuario o email ya existen.")

    hashed_pw = auth.get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_pw
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    return {"message": "Usuario registrado correctamente", "user_id": new_user.id}


# -----------------------------
# Login (genera token JWT)
# -----------------------------
@router.post("/login")
def login_user(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    ip = request.client.host

    # Rate limit: 10 intentos/minuto/IP
    if auth.rate_limited(ip, auth.LOGIN_LIMIT, 10, 60):
        raise HTTPException(status_code=429, detail="Demasiados intentos de login. Intenta más tarde.")

    statement = select(User).where(User.username == form_data.username)
    user = session.exec(statement).first()

    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    access_token = auth.create_access_token({"sub": user.username, "user_id": user.id})

    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/refresh")
def refresh_token(request: Request, token: str, session: Session = Depends(get_session)):
    """Recibe un refresh token y retorna un nuevo access token."""
    payload = auth.verify_refresh_token(token)
    username = payload.get("sub")
    user = auth.get_user_by_username(session, username)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    # Genera nuevo access token de 24h
    access_token = auth.create_access_token({"sub": user.username, "user_id": user.id})
    return {"access_token": access_token, "token_type": "bearer"}


# -----------------------------
# Endpoint protegido (requiere token)
# -----------------------------
@router.get("/me")
def get_me(current_user: User = Depends(auth.get_current_user)):
    """Devuelve los datos del usuario autenticado"""
    return {
        "username": current_user.username,
        "email": current_user.email,
        "id": current_user.id
    }
