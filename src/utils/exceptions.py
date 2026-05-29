"""
Excepciones personalizadas de la aplicación.

Jerarquía:
    AppError
    ├── AuthenticationError
    ├── AuthorizationError
    ├── NotFoundError
    ├── ValidationError
    ├── DuplicateError
    └── BusinessLogicError
"""


class AppError(Exception):
    """Excepción base de la aplicación."""

    def __init__(self, message: str = "Error interno de la aplicación") -> None:
        self.message = message
        super().__init__(self.message)


class AuthenticationError(AppError):
    """Credenciales inválidas o sesión expirada."""

    def __init__(self, message: str = "Credenciales inválidas") -> None:
        super().__init__(message)


class AuthorizationError(AppError):
    """El usuario no tiene permisos suficientes."""

    def __init__(self, message: str = "No tienes permisos para esta acción") -> None:
        super().__init__(message)


class NotFoundError(AppError):
    """Recurso no encontrado."""

    def __init__(self, resource: str = "Recurso", resource_id: int | str = "") -> None:
        msg = f"{resource} no encontrado"
        if resource_id:
            msg = f"{resource} con ID {resource_id} no encontrado"
        super().__init__(msg)


class ValidationError(AppError):
    """Datos de entrada inválidos."""

    def __init__(self, message: str = "Datos inválidos") -> None:
        super().__init__(message)


class DuplicateError(AppError):
    """Recurso duplicado (ej: email ya registrado)."""

    def __init__(self, field: str = "registro", value: str = "") -> None:
        msg = f"El {field} '{value}' ya existe" if value else f"El {field} ya existe"
        super().__init__(msg)


class BusinessLogicError(AppError):
    """Violación de regla de negocio."""

    def __init__(self, message: str = "Operación no permitida") -> None:
        super().__init__(message)
