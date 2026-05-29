"""
Repositorio base genérico — CRUD reutilizable.

Todos los repositorios específicos heredan de aquí,
obteniendo operaciones CRUD sin repetir código.
"""

from typing import TypeVar, Generic, Type

from sqlalchemy.orm import Session

from config.database import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """
    Repositorio genérico con operaciones CRUD básicas.

    Uso:
        class UserRepository(BaseRepository[User]):
            def __init__(self, session: Session):
                super().__init__(User, session)
    """

    def __init__(self, model: Type[T], session: Session) -> None:
        self._model = model
        self._session = session

    # ── Read ────────────────────────────────────────────────
    def get(self, entity_id: int) -> T | None:
        """Obtener entidad por ID."""
        return self._session.get(self._model, entity_id)

    def get_all(self, *, skip: int = 0, limit: int = 100) -> list[T]:
        """Obtener lista paginada de entidades."""
        return (
            self._session.query(self._model)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count(self) -> int:
        """Contar total de entidades."""
        return self._session.query(self._model).count()

    # ── Create ──────────────────────────────────────────────
    def create(self, entity: T) -> T:
        """Insertar nueva entidad y hacer commit."""
        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity

    # ── Update ──────────────────────────────────────────────
    def update(self, entity: T, data: dict) -> T:
        """Actualizar campos de una entidad existente."""
        for key, value in data.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        self._session.commit()
        self._session.refresh(entity)
        return entity

    # ── Delete ──────────────────────────────────────────────
    def delete(self, entity: T) -> None:
        """Eliminar entidad."""
        self._session.delete(entity)
        self._session.commit()

    def delete_by_id(self, entity_id: int) -> bool:
        """Eliminar entidad por ID. Retorna True si existía."""
        entity = self.get(entity_id)
        if entity:
            self.delete(entity)
            return True
        return False

    # ── Helpers ─────────────────────────────────────────────
    def flush(self) -> None:
        """Flush sin commit (útil dentro de transacciones)."""
        self._session.flush()

    def rollback(self) -> None:
        """Rollback de la transacción actual."""
        self._session.rollback()
