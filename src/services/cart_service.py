"""
Servicio de Carrito de Compras.

Gestión completa del carrito: agregar, remover, actualizar cantidades, calcular total.
"""

from sqlalchemy.orm import Session

from src.models.cart import Cart, CartItem
from src.models.menu_item import MenuItem
from src.repositories.cart_repository import CartRepository
from src.repositories.menu_repository import MenuRepository
from src.utils.logger import logger
from src.utils.exceptions import (
    NotFoundError,
    BusinessLogicError,
)


class CartService:
    """Servicio de carrito — dependency injection vía constructor."""

    def __init__(self, session: Session) -> None:
        self._cart_repo = CartRepository(session)
        self._menu_repo = MenuRepository(session)

    def get_cart(self, user_id: int) -> Cart:
        """Obtener carrito del usuario (lo crea si no existe)."""
        return self._cart_repo.get_or_create(user_id)

    def add_item(self, user_id: int, menu_item_id: int, quantity: int = 1) -> CartItem:
        """
        Agregar item al carrito.

        Args:
            user_id: ID del usuario dueño del carrito.
            menu_item_id: ID del item del menú.
            quantity: Cantidad a agregar.

        Raises:
            NotFoundError: Si el item no existe.
            BusinessLogicError: Si el item no está disponible.
        """
        menu_item = self._menu_repo.get(menu_item_id)
        if menu_item is None:
            raise NotFoundError("Item del menú", menu_item_id)

        if not menu_item.is_available:
            raise BusinessLogicError(
                f"'{menu_item.name}' no está disponible actualmente"
            )

        cart = self._cart_repo.get_or_create(user_id)
        cart_item = self._cart_repo.add_item(cart, menu_item_id, quantity)
        logger.info(
            f"Item '{menu_item.name}' x{quantity} agregado al carrito "
            f"(user_id={user_id})"
        )
        return cart_item

    def remove_item(self, user_id: int, menu_item_id: int) -> bool:
        """Remover item del carrito."""
        cart = self._cart_repo.get_or_create(user_id)
        removed = self._cart_repo.remove_item(cart, menu_item_id)
        if removed:
            logger.info(
                f"Item menu_id={menu_item_id} removido del carrito "
                f"(user_id={user_id})"
            )
        return removed

    def update_quantity(
        self, user_id: int, menu_item_id: int, quantity: int
    ) -> CartItem | None:
        """Actualizar cantidad de un item en el carrito."""
        cart = self._cart_repo.get_or_create(user_id)
        return self._cart_repo.update_item_quantity(cart, menu_item_id, quantity)

    def clear_cart(self, user_id: int) -> None:
        """Vaciar completamente el carrito."""
        cart = self._cart_repo.get_or_create(user_id)
        self._cart_repo.clear(cart)
        logger.info(f"Carrito vaciado (user_id={user_id})")

    def get_total(self, user_id: int) -> float:
        """Calcular el total del carrito."""
        cart = self._cart_repo.get_or_create(user_id)
        total = 0.0
        for item in cart.items:
            if item.menu_item:
                total += item.menu_item.price * item.quantity
        return round(total, 2)

    def get_item_count(self, user_id: int) -> int:
        """Obtener cantidad total de items en el carrito."""
        cart = self._cart_repo.get_or_create(user_id)
        return sum(item.quantity for item in cart.items)

    def get_cart_summary(self, user_id: int) -> list[dict]:
        """
        Obtener resumen detallado del carrito.

        Returns:
            Lista de dicts con name, price, quantity, subtotal.
        """
        cart = self._cart_repo.get_or_create(user_id)
        summary = []
        for item in cart.items:
            if item.menu_item:
                summary.append({
                    "menu_item_id": item.menu_item.id,
                    "name": item.menu_item.name,
                    "price": item.menu_item.price,
                    "quantity": item.quantity,
                    "subtotal": round(item.menu_item.price * item.quantity, 2),
                })
        return summary
