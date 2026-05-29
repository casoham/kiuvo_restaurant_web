"""
Dependencias de FastAPI — inyección de sesión y autenticación.

Estas dependencias NO viven en la capa de servicios;
son exclusivas de la capa de presentación (API).
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from config.database import SessionLocal
from src.models.user import User, UserRole
from src.repositories.user_repository import UserRepository
from src.utils.jwt import decode_token
from src.utils.exceptions import AuthenticationError


# ── Esquema OAuth2 ──────────────────────────────────────────
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ── Sesión de BD ────────────────────────────────────────────
def get_db():
    """Genera una sesión de BD para cada request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DBSession = Annotated[Session, Depends(get_db)]


# ── Usuario actual ──────────────────────────────────────────
def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DBSession,
) -> User:
    """
    Obtener el usuario autenticado a partir del token JWT.

    Raises:
        HTTPException 401: Token inválido, usuario no encontrado o inactivo.
    """
    try:
        payload = decode_token(token)
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tipo de token inválido — se requiere access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sin identificador de usuario",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_repo = UserRepository(db)
    user = user_repo.get(int(user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta desactivada",
        )

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


# ── Verificadores de rol ────────────────────────────────────
def require_admin(current_user: CurrentUser) -> User:
    """Requiere rol ADMIN."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vos no pertenecesis aqui",
        )
    return current_user


def require_staff_or_admin(current_user: CurrentUser) -> User:
    """Requiere rol STAFF o ADMIN."""
    if current_user.role not in (UserRole.STAFF, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de staff o administrador",
        )
    return current_user


AdminUser = Annotated[User, Depends(require_admin)]
StaffUser = Annotated[User, Depends(require_staff_or_admin)]
