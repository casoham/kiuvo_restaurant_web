"""
Utilidades JWT — creación y verificación de tokens.

Desacoplado de FastAPI: solo usa python-jose y config.
"""

from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError

from config.settings import settings
from src.utils.exceptions import AuthenticationError


def create_access_token(user_id: int, role: str) -> str:
    """
    Crear un JWT de acceso.

    Args:
        user_id: ID del usuario.
        role: Rol del usuario.

    Returns:
        Token JWT codificado.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """
    Crear un JWT de refresh.

    Args:
        user_id: ID del usuario.

    Returns:
        Token JWT de refresh codificado.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decodificar y validar un token JWT.

    Args:
        token: Token JWT codificado.

    Returns:
        Payload decodificado.

    Raises:
        AuthenticationError: Si el token es inválido o expirado.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError as e:
        raise AuthenticationError(f"Token inválido o expirado: {e}")
