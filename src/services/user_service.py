"""
Servicio de gestión de Usuarios.

CRUD completo + operaciones de administración (cambio de roles, desactivación).
"""

from sqlalchemy.orm import Session

from src.models.user import User, UserRole
from src.repositories.user_repository import UserRepository
from src.utils.logger import logger
from src.utils.exceptions import (
    NotFoundError,
    AuthorizationError,
    DuplicateError,
)


class UserService:
    """Servicio de usuarios — dependency injection vía constructor."""

    def __init__(self, session: Session) -> None:
        self._repo = UserRepository(session)

    # ── Lectura ─────────────────────────────────────────────
    def get_by_id(self, user_id: int) -> User:
        """Obtener usuario por ID o lanzar NotFoundError."""
        user = self._repo.get(user_id)
        if user is None:
            raise NotFoundError("Usuario", user_id)
        return user

    def get_all(self, *, skip: int = 0, limit: int = 100) -> list[User]:
        """Listar todos los usuarios."""
        return self._repo.get_all(skip=skip, limit=limit)

    def get_by_role(self, role: UserRole) -> list[User]:
        """Listar usuarios por rol."""
        return self._repo.get_by_role(role)

    # ── Actualización ───────────────────────────────────────
    def update_profile(self, user: User, data: dict) -> User:
        """Actualizar perfil de usuario (email, username)."""
        if "email" in data and data["email"]:
            existing = self._repo.get_by_email(data["email"])
            if existing and existing.id != user.id:
                raise DuplicateError("email", data["email"])

        if "username" in data and data["username"]:
            existing = self._repo.get_by_username(data["username"])
            if existing and existing.id != user.id:
                raise DuplicateError("username", data["username"])

        # No permitir cambio de rol desde aquí
        data.pop("role", None)
        data.pop("password_hash", None)

        updated = self._repo.update(user, data)
        logger.info(f"Perfil actualizado: {updated.username}")
        return updated

    # ── Administración (solo ADMIN) ─────────────────────────
    def change_role(
        self, admin: User, target_user_id: int, new_role: UserRole
    ) -> User:
        """
        Cambiar rol de un usuario. Solo ADMIN puede hacerlo.

        Args:
            admin: Usuario que ejecuta la acción (debe ser ADMIN).
            target_user_id: ID del usuario a modificar.
            new_role: Nuevo rol.
        """
        if admin.role != UserRole.ADMIN:
            raise AuthorizationError("Solo un administrador puede cambiar roles")

        target = self.get_by_id(target_user_id)
        updated = self._repo.change_role(target, new_role)
        logger.info(
            f"Rol cambiado: {updated.username} → {new_role.value} "
            f"(por admin: {admin.username})"
        )
        return updated

    def deactivate_user(self, admin: User, target_user_id: int) -> User:
        """Desactivar usuario (soft delete). Solo ADMIN."""
        if admin.role != UserRole.ADMIN:
            raise AuthorizationError("Solo un administrador puede desactivar usuarios")

        target = self.get_by_id(target_user_id)
        deactivated = self._repo.deactivate(target)
        logger.info(
            f"Usuario desactivado: {deactivated.username} "
            f"(por admin: {admin.username})"
        )
        return deactivated

    def activate_user(self, admin: User, target_user_id: int) -> User:
        """Reactivar un usuario desactivado. Solo ADMIN."""
        if admin.role != UserRole.ADMIN:
            raise AuthorizationError("Solo un administrador puede activar usuarios")

        target = self.get_by_id(target_user_id)
        activated = self._repo.update(target, {"is_active": True})
        logger.info(
            f"Usuario reactivado: {activated.username} "
            f"(por admin: {admin.username})"
        )
        return activated

    # ── Eliminación ─────────────────────────────────────────
    def delete_user(self, admin: User, target_user_id: int) -> None:
        """Eliminar usuario permanentemente. Solo ADMIN."""
        if admin.role != UserRole.ADMIN:
            raise AuthorizationError("Solo un administrador puede eliminar usuarios")

        target = self.get_by_id(target_user_id)
        self._repo.delete(target)
        logger.info(
            f"Usuario eliminado: {target.username} (por admin: {admin.username})"
        )
