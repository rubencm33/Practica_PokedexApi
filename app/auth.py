# app/auth.py
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlmodel import Session, select

from app.config import settings
from app.database import get_session
from app.models import User

# -----------------------------
# Configuración de seguridad
# -----------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# -----------------------------
# Limitadores de peticiones
# -----------------------------
REGISTER_LIMIT: Dict[str, list] = {}
LOGIN_LIMIT: Dict[str, list] = {}


# -----------------------------
# Validaciones
# -----------------------------
def verify_email(email: str) -> bool:
    """Valida el formato del email."""
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, email) is not None


def verify_password_strength(password: str) -> bool:
    """Verifica que la contraseña sea segura."""
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"\d", password):
        return False
    return True


# -----------------------------
# Hashing y verificación
# -----------------------------
def get_password_hash(password: str) -> str:
    if len(password.encode("utf-8")) > 72:
        password = password[:72]
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# -----------------------------
# Tokens JWT
# -----------------------------
def create_access_token(data: dict, expires_delta: timedelta = timedelta(hours=24)):
    """Genera un token JWT con expiración."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# -----------------------------
# Rate limit simple por IP
# -----------------------------
def rate_limited(ip: str, limit_dict: Dict[str, list], limit: int, seconds: int) -> bool:
    """Limita la cantidad de peticiones por IP en un tiempo determinado."""
    now = time.time()
    timestamps = [t for t in limit_dict.get(ip, []) if now - t < seconds]
    if len(timestamps) >= limit:
        return True
    timestamps.append(now)
    limit_dict[ip] = timestamps
    return False


# -----------------------------
# Obtener usuario desde la BD
# -----------------------------
def get_user_by_username(session: Session, username: str) -> Optional[User]:
    statement = select(User).where(User.username == username)
    return session.exec(statement).first()


# -----------------------------
# Obtener usuario autenticado
# -----------------------------
async def get_current_user(
    credentials=Depends(security),
    session: Session = Depends(get_session)
) -> User:
    """Obtiene el usuario autenticado desde el token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        username = payload.get("sub")
        if not username:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user_by_username(session, username)
    if not user:
        raise credentials_exception
    return user
# Tiempo de expiración
ACCESS_TOKEN_EXPIRE_HOURS = 24
REFRESH_TOKEN_EXPIRE_DAYS = 7

def create_refresh_token(data: dict, expires_delta: timedelta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)):
    """Genera un refresh token con expiración de 7 días."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

async def verify_refresh_token(token: str) -> dict:
    """Decodifica y valida un refresh token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Refresh token inválido")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Refresh token inválido")
