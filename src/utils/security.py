"""
Utilidades de seguridad — hashing de contraseñas.

Usa bcrypt para hash y verificación.
Preparado para integración con JWT en el futuro.
"""

import bcrypt

from config.settings import settings


def hash_password(password: str) -> str:
    """
    Generar hash bcrypt de una contraseña.

    Args:
        password: Contraseña en texto plano.

    Returns:
        Hash bcrypt como string.
    """
    salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """
    Verificar una contraseña contra su hash.

    Args:
        password: Contraseña en texto plano.
        hashed: Hash bcrypt almacenado.

    Returns:
        True si coincide, False si no.
    """
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


# ── JWT Placeholders ────────────────────────────────────────
# TODO: JWT token generation
#
# from datetime import datetime, timedelta
# import jwt  # pip install PyJWT
#
# def create_access_token(data: dict) -> str:
#     """Crear token JWT."""
#     to_encode = data.copy()
#     expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
#     to_encode.update({"exp": expire})
#     return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
#
# def decode_access_token(token: str) -> dict:
#     """Decodificar y validar token JWT."""
#     return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
