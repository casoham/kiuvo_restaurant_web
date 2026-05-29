"""
Servicio de Autenticación y Autorización.

Responsable de registro, login, y verificación de credenciales.
Preparado para integración con JWT.
"""

import re
from datetime import date

from sqlalchemy.orm import Session

from src.models.user import User, UserRole
from src.repositories.user_repository import UserRepository
from src.utils.security import hash_password, verify_password
from src.utils.logger import logger
from src.utils.exceptions import (
    AuthenticationError,
    DuplicateError,
    ValidationError,
)

# Patrón de email institucional para clientes
_INSTITUTIONAL_EMAIL_RE = re.compile(
    r"^[a-záéíóúñü]+\.[a-záéíóúñü]+@keyinstitute\.edu\.sv$"
)


class AuthService:
    """Servicio de autenticación — dependency injection vía constructor."""

    def __init__(self, session: Session) -> None:
        self._repo = UserRepository(session)
        self._session = session

    # ── Validaciones internas ───────────────────────────────

    @staticmethod
    def _validate_password(password: str) -> None:
        """Validar que la contraseña cumpla requisitos mínimos."""
        if len(password) < 6:
            raise ValidationError("La contraseña debe tener al menos 6 caracteres")
        if not any(c.isupper() for c in password):
            raise ValidationError("La contraseña debe contener al menos una letra mayúscula")
        if not any(c.islower() for c in password):
            raise ValidationError("La contraseña debe contener al menos una letra minúscula")

    @staticmethod
    def validate_institutional_email(email: str) -> str:
        """
        Validar formato de email institucional: nombre.apellido@keyinstitute.edu.sv

        Returns:
            El email normalizado (en minúsculas).

        Raises:
            ValidationError: Si el formato es inválido.
        """
        email = email.lower().strip()
        if not _INSTITUTIONAL_EMAIL_RE.match(email):
            raise ValidationError(
                "El email debe tener el formato nombre.apellido@keyinstitute.edu.sv"
            )
        return email

    @staticmethod
    def generate_username_from_email(email: str) -> str:
        """
        Generar username automáticamente a partir del email institucional.

        Ejemplo: juan.perez@keyinstitute.edu.sv → juan_perez
        """
        local_part = email.split("@")[0]
        return local_part.replace(".", "_")

    # ── Registro general (compatible con seeds) ─────────────

    def register(
        self,
        email: str,
        username: str,
        password: str,
        student_id: str = "",
        birth_date: date | None = None,
        role: UserRole = UserRole.USER,
        major: str | None = None,
    ) -> User:
        """
        Registrar un nuevo usuario (método general, usado por seeds y admin).

        Args:
            email: Email único.
            username: Nombre de usuario único.
            password: Contraseña en texto plano (se hashea internamente).
            student_id: Carnet universitario único.
            birth_date: Fecha de nacimiento (opcional).
            role: Rol del usuario (por defecto USER).
            major: Carrera universitaria (requerido para USER).

        Returns:
            El usuario creado.

        Raises:
            DuplicateError: Si email, username o student_id ya existen.
            ValidationError: Si los datos son inválidos.
        """
        # Validaciones de contraseña
        self._validate_password(password)

        if not student_id or not student_id.strip():
            raise ValidationError("El carnet universitario es requerido")
        if not re.fullmatch(r"Key_[A-Za-z0-9]{6}", student_id.strip()):
            raise ValidationError(
                "El carnet universitario debe tener el formato Key_xxxxxx "
                "(Key_ seguido de exactamente 6 caracteres alfanuméricos, ej: Key_AB1234)"
            )

        if role == UserRole.USER:
            if not major or not major.strip():
                raise ValidationError("La carrera universitaria es requerida")
            from src.dto.schemas import VALID_MAJORS
            if major not in VALID_MAJORS:
                raise ValidationError(
                    f"Carrera no válida. Debe ser una de: {', '.join(VALID_MAJORS)}"
                )

        if self._repo.get_by_email(email):
            raise DuplicateError("email", email)

        if self._repo.get_by_username(username):
            raise DuplicateError("username", username)

        if self._repo.get_by_student_id(student_id.strip()):
            raise DuplicateError("carnet (student_id)", student_id)

        # Crear usuario
        user = User(
            email=email.lower().strip(),
            username=username.strip(),
            password_hash=hash_password(password),
            student_id=student_id.strip(),
            birth_date=birth_date,
            role=role,
            major=major,
        )
        created = self._repo.create(user)
        logger.info(
            f"Usuario registrado: {created.username} "
            f"(carnet: {created.student_id}, rol: {created.role.value})"
        )
        return created

    # ── Registro de cliente (desde CLI) ─────────────────────

    def register_client(
        self,
        email: str,
        password: str,
        student_id: str,
        birth_date: date | None = None,
        major: str = "",
    ) -> User:
        """
        Registrar un nuevo cliente (usuario regular).

        El email debe ser institucional (nombre.apellido@keyinstitute.edu.sv).
        El username se genera automáticamente a partir del email.

        Args:
            email: Email institucional.
            password: Contraseña (mín. 6 caracteres, mayúsculas y minúsculas).
            student_id: Carnet universitario (Key_xxxxxx).
            birth_date: Fecha de nacimiento (opcional).
            major: Carrera universitaria.

        Returns:
            El usuario creado.
        """
        # Validar email institucional
        email = self.validate_institutional_email(email)
        # Generar username automático
        username = self.generate_username_from_email(email)

        return self.register(
            email=email,
            username=username,
            password=password,
            student_id=student_id,
            birth_date=birth_date,
            role=UserRole.USER,
            major=major,
        )

    # ── Registro de staff (desde CLI) ───────────────────────

    def register_staff(
        self,
        full_name: str,
        password: str,
        student_id: str,
    ) -> User:
        """
        Registrar un nuevo miembro de staff.

        No requiere email ni carnet; usa el ID presencial asignado (student_id).
        El email se genera internamente como placeholder.

        Args:
            full_name: Nombre completo del staff.
            password: Contraseña (mín. 6 caracteres, mayúsculas y minúsculas).
            student_id: ID presencial asignado (Key_xxxxxx).

        Returns:
            El usuario creado.
        """
        self._validate_password(password)

        if not student_id or not student_id.strip():
            raise ValidationError("El ID presencial es requerido")
        if not re.fullmatch(r"Key_[A-Za-z0-9]{6}", student_id.strip()):
            raise ValidationError(
                "El ID presencial debe tener el formato Key_xxxxxx "
                "(Key_ seguido de exactamente 6 caracteres alfanuméricos, ej: Key_STF001)"
            )

        # Generar username y email placeholder a partir del nombre
        username = full_name.lower().strip().replace(" ", "_")
        email = f"{username}@staff.doeat.local"

        if self._repo.get_by_email(email):
            raise DuplicateError("email", email)
        if self._repo.get_by_username(username):
            raise DuplicateError("username", username)
        if self._repo.get_by_student_id(student_id.strip()):
            raise DuplicateError("ID presencial (student_id)", student_id)

        user = User(
            email=email,
            username=username,
            password_hash=hash_password(password),
            student_id=student_id.strip(),
            birth_date=None,
            role=UserRole.STAFF,
        )
        created = self._repo.create(user)
        logger.info(
            f"Staff registrado: {created.username} "
            f"(ID presencial: {created.student_id})"
        )
        return created

    def login(self, username: str, password: str) -> User:
        """
        Autenticar un usuario.

        Args:
            username: Nombre de usuario.
            password: Contraseña en texto plano.

        Returns:
            El usuario autenticado.

        Raises:
            AuthenticationError: Si las credenciales son inválidas o la cuenta está desactivada.
        """
        user = self._repo.get_by_username(username.strip())

        if user is None:
            logger.warning(f"Intento de login fallido: usuario '{username}' no existe")
            raise AuthenticationError("Usuario o contraseña incorrectos")

        if not user.is_active:
            logger.warning(f"Intento de login a cuenta desactivada: {username}")
            raise AuthenticationError("Esta cuenta está desactivada")

        if not verify_password(password, user.password_hash):
            logger.warning(f"Intento de login fallido: contraseña incorrecta para '{username}'")
            raise AuthenticationError("Usuario o contraseña incorrectos")

        logger.info(f"Login exitoso: {user.username}")

        # TODO: JWT token generation
        # token = create_access_token({"sub": user.id, "role": user.role.value})
        # return user, token

        return user

    def change_password(
        self, user: User, old_password: str, new_password: str
    ) -> None:
        """Cambiar contraseña de un usuario."""
        if not verify_password(old_password, user.password_hash):
            raise AuthenticationError("Contraseña actual incorrecta")

        if len(new_password) < 6:
            raise ValidationError("La nueva contraseña debe tener al menos 6 caracteres")

        self._repo.update(user, {"password_hash": hash_password(new_password)})
        logger.info(f"Contraseña cambiada para: {user.username}")

    def change_password_by_email(self, email: str, new_password: str) -> None:
        """
        Cambiar contraseña de un usuario usando su email.

        Args:
            email: Email del usuario.
            new_password: Nueva contraseña.

        Raises:
            ValidationError: Si la contraseña no cumple requisitos.
            AuthenticationError: Si el email no existe.
        """
        self._validate_password(new_password)

        user = self._repo.get_by_email(email.lower().strip())
        if user is None:
            raise AuthenticationError("No se encontró un usuario con ese email")

        self._repo.update(user, {"password_hash": hash_password(new_password)})
        logger.info(f"Contraseña restablecida para: {user.username} (vía email)")
