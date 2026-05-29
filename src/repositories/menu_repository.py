"""
Repositorio de Items del Menú.
"""

from sqlalchemy.orm import Session

from src.models.menu_item import MenuItem, MenuCategory
from src.repositories.base import BaseRepository


class MenuRepository(BaseRepository[MenuItem]):

    def __init__(self, session: Session) -> None:
        super().__init__(MenuItem, session)

    def get_by_category(self, category: MenuCategory) -> list[MenuItem]:
        """Obtener items por categoría."""
        return (
            self._session.query(MenuItem)
            .filter(MenuItem.category == category, MenuItem.is_available.is_(True))
            .all()
        )

    def get_available(self) -> list[MenuItem]:
        """Obtener todos los items disponibles."""
        return (
            self._session.query(MenuItem)
            .filter(MenuItem.is_available.is_(True))
            .order_by(MenuItem.category, MenuItem.name)
            .all()
        )

    def get_featured(self) -> list[MenuItem]:
        """Obtener items destacados."""
        return (
            self._session.query(MenuItem)
            .filter(MenuItem.is_featured.is_(True), MenuItem.is_available.is_(True))
            .all()
        )

    def get_new_items(self) -> list[MenuItem]:
        """Obtener items marcados como nuevos."""
        return (
            self._session.query(MenuItem)
            .filter(MenuItem.is_new.is_(True), MenuItem.is_available.is_(True))
            .all()
        )

    def search_by_name(self, query: str) -> list[MenuItem]:
        """Buscar items por nombre (parcial, case-insensitive)."""
        return (
            self._session.query(MenuItem)
            .filter(MenuItem.name.ilike(f"%{query}%"))
            .all()
        )

    def toggle_availability(self, item: MenuItem) -> MenuItem:
        """Alternar disponibilidad de un item."""
        return self.update(item, {"is_available": not item.is_available})
