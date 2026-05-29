"""
Repositorio de Usuarios.
"""

from sqlalchemy.orm import Session

from src.models.user import User, UserRole
from src.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):

    def __init__(self, session: Session) -> None:
        super().__init__(User, session)

    def get_by_email(self, email: str) -> User | None:
        """Buscar usuario por email."""
        return (
            self._session.query(User)
            .filter(User.email == email)
            .first()
        )

    def get_by_username(self, username: str) -> User | None:
        """Buscar usuario por username."""
        return (
            self._session.query(User)
            .filter(User.username == username)
            .first()
        )

    def get_active_users(self) -> list[User]:
        """Obtener todos los usuarios activos."""
        return (
            self._session.query(User)
            .filter(User.is_active.is_(True))
            .all()
        )

    def get_by_role(self, role: UserRole) -> list[User]:
        """Obtener usuarios por rol."""
        return (
            self._session.query(User)
            .filter(User.role == role)
            .all()
        )

    def deactivate(self, user: User) -> User:
        """Desactivar un usuario (soft delete)."""
        return self.update(user, {"is_active": False})

    def change_role(self, user: User, new_role: UserRole) -> User:
        """Cambiar el rol de un usuario."""
        return self.update(user, {"role": new_role})

    def get_by_student_id(self, student_id: str) -> User | None:
        """Buscar usuario por carnet universitario."""
        return (
            self._session.query(User)
            .filter(User.student_id == student_id)
            .first()
        )
