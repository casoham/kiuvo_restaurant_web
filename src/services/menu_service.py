"""
Servicio de gestión del Menú.

CRUD completo + filtros por categoría, disponibilidad, destacados, nuevos.
"""

from sqlalchemy.orm import Session

from src.models.menu_item import MenuItem, MenuCategory
from src.models.user import User, UserRole
from src.repositories.menu_repository import MenuRepository
from src.utils.logger import logger
from src.utils.exceptions import (
    NotFoundError,
    AuthorizationError,
    ValidationError,
)


class MenuService:
    """Servicio de menú — dependency injection vía constructor."""

    # Roles que pueden gestionar el menú
    _MANAGER_ROLES = {UserRole.ADMIN, UserRole.STAFF}

    def __init__(self, session: Session) -> None:
        self._repo = MenuRepository(session)

    # ── Helpers de autorización ──────────────────────────────
    def _require_manager(self, user: User) -> None:
        """Verificar que el usuario puede gestionar el menú."""
        if user.role not in self._MANAGER_ROLES:
            raise AuthorizationError(
                "Solo ADMIN o STAFF pueden gestionar el menú"
            )

    # ── Lectura (pública) ───────────────────────────────────
    def get_by_id(self, item_id: int) -> MenuItem:
        """Obtener item por ID o lanzar NotFoundError."""
        item = self._repo.get(item_id)
        if item is None:
            raise NotFoundError("Item del menú", item_id)
        return item

    def get_all(self) -> list[MenuItem]:
        """Obtener todos los items (incluidos no disponibles, para admin)."""
        return self._repo.get_all(limit=500)

    def get_available(self) -> list[MenuItem]:
        """Obtener solo items disponibles (para clientes)."""
        return self._repo.get_available()

    def get_by_category(self, category: MenuCategory) -> list[MenuItem]:
        """Obtener items por categoría."""
        return self._repo.get_by_category(category)

    def get_featured(self) -> list[MenuItem]:
        """Obtener items destacados."""
        return self._repo.get_featured()

    def get_new_items(self) -> list[MenuItem]:
        """Obtener items nuevos."""
        return self._repo.get_new_items()

    def search(self, query: str) -> list[MenuItem]:
        """Buscar items por nombre."""
        return self._repo.search_by_name(query)

    # ── Escritura (solo ADMIN/STAFF) ────────────────────────
    def create_item(self, user: User, data: dict) -> MenuItem:
        """Crear un nuevo item de menú."""
        self._require_manager(user)

        if data.get("price", 0) <= 0:
            raise ValidationError("El precio debe ser mayor a 0")

        item = MenuItem(**data)
        created = self._repo.create(item)
        logger.info(f"Item creado: {created.name} (por: {user.username})")
        return created

    def update_item(self, user: User, item_id: int, data: dict) -> MenuItem:
        """Actualizar un item existente."""
        self._require_manager(user)

        item = self.get_by_id(item_id)
        if "price" in data and data["price"] is not None and data["price"] <= 0:
            raise ValidationError("El precio debe ser mayor a 0")

        # Filtrar None values
        clean_data = {k: v for k, v in data.items() if v is not None}
        updated = self._repo.update(item, clean_data)
        logger.info(f"Item actualizado: {updated.name} (por: {user.username})")
        return updated

    def toggle_availability(self, user: User, item_id: int) -> MenuItem:
        """Alternar disponibilidad de un item."""
        self._require_manager(user)

        item = self.get_by_id(item_id)
        toggled = self._repo.toggle_availability(item)
        status = "disponible" if toggled.is_available else "no disponible"
        logger.info(f"Item '{toggled.name}' ahora está {status} (por: {user.username})")
        return toggled

    def toggle_featured(self, user: User, item_id: int) -> MenuItem:
        """Alternar estado destacado de un item."""
        self._require_manager(user)

        item = self.get_by_id(item_id)
        new_val = not item.is_featured
        updated = self._repo.update(item, {"is_featured": new_val})
        status = "destacado ⭐" if updated.is_featured else "no destacado"
        logger.info(f"Item '{updated.name}' ahora está {status} (por: {user.username})")
        return updated

    def toggle_new(self, user: User, item_id: int) -> MenuItem:
        """Alternar estado de 'nuevo' para promociones de temporada."""
        self._require_manager(user)

        item = self.get_by_id(item_id)
        new_val = not item.is_new
        updated = self._repo.update(item, {"is_new": new_val})
        status = "nuevo 🆕" if updated.is_new else "normal"
        logger.info(f"Item '{updated.name}' ahora está marcado como {status} (por: {user.username})")
        return updated

    def delete_item(self, user: User, item_id: int) -> None:
        """Eliminar un item del menú."""
        self._require_manager(user)

        item = self.get_by_id(item_id)
        self._repo.delete(item)
        logger.info(f"Item eliminado: {item.name} (por: {user.username})")
