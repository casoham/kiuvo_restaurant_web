"""
Manejadores de excepciones — mapeo de excepciones del dominio a HTTP.

Convierte las excepciones de negocio (AppError y subclases) en
respuestas HTTP apropiadas, manteniendo la capa de servicios
desacoplada de FastAPI.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse

from src.utils.exceptions import (
    AppError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ValidationError,
    DuplicateError,
    BusinessLogicError,
)

# SQLAlchemy / DB errors (evitar 500 genérico)
from sqlalchemy.exc import IntegrityError, DataError, DBAPIError

# Mapeo excepción → código HTTP
_STATUS_MAP: dict[type, int] = {
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    AuthorizationError: status.HTTP_403_FORBIDDEN,
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ValidationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    DuplicateError: status.HTTP_409_CONFLICT,
    BusinessLogicError: status.HTTP_400_BAD_REQUEST,
}


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    """Convertir cualquier AppError en respuesta JSON."""
    http_status = _STATUS_MAP.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)
    return JSONResponse(
        status_code=http_status,
        content={"detail": exc.message},
    )


async def sqlalchemy_error_handler(_request: Request, exc: DBAPIError) -> JSONResponse:
    """
    Convertir errores de BD a respuestas útiles.

    - IntegrityError: duplicados/constraints -> 409
    - DataError: datos inválidos (ej. enum) -> 422
    - Otros DBAPIError -> 500
    """
    if isinstance(exc, IntegrityError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": "Conflicto en base de datos (registro duplicado o restricción)."},
        )
    if isinstance(exc, DataError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Datos inválidos para la base de datos."},
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Error de base de datos."},
    )
