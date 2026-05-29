"""
Repositorio de Carrito de Compras.
"""

from sqlalchemy.orm import Session, joinedload

from src.models.cart import Cart, CartItem
from src.repositories.base import BaseRepository


class CartRepository(BaseRepository[Cart]):

    def __init__(self, session: Session) -> None:
        super().__init__(Cart, session)

    def get_by_user(self, user_id: int) -> Cart | None:
        """Obtener carrito de un usuario (con items cargados)."""
        return (
            self._session.query(Cart)
            .options(joinedload(Cart.items).joinedload(CartItem.menu_item))
            .filter(Cart.user_id == user_id)
            .first()
        )

    def get_or_create(self, user_id: int) -> Cart:
        """Obtener carrito existente o crear uno nuevo."""
        cart = self.get_by_user(user_id)
        if cart is None:
            cart = Cart(user_id=user_id)
            self.create(cart)
        return cart

    def add_item(self, cart: Cart, menu_item_id: int, quantity: int = 1) -> CartItem:
        """Agregar item al carrito (o sumar cantidad si ya existe)."""
        existing = (
            self._session.query(CartItem)
            .filter(
                CartItem.cart_id == cart.id,
                CartItem.menu_item_id == menu_item_id,
            )
            .first()
        )
        if existing:
            existing.quantity += quantity
            self._session.commit()
            self._session.refresh(existing)
            return existing

        item = CartItem(cart_id=cart.id, menu_item_id=menu_item_id, quantity=quantity)
        self._session.add(item)
        self._session.commit()
        self._session.refresh(item)
        return item

    def remove_item(self, cart: Cart, menu_item_id: int) -> bool:
        """Remover item del carrito. Retorna True si existía."""
        item = (
            self._session.query(CartItem)
            .filter(
                CartItem.cart_id == cart.id,
                CartItem.menu_item_id == menu_item_id,
            )
            .first()
        )
        if item:
            self._session.delete(item)
            self._session.commit()
            return True
        return False

    def update_item_quantity(
        self, cart: Cart, menu_item_id: int, quantity: int
    ) -> CartItem | None:
        """Actualizar cantidad de un item. Si quantity <= 0, lo elimina."""
        item = (
            self._session.query(CartItem)
            .filter(
                CartItem.cart_id == cart.id,
                CartItem.menu_item_id == menu_item_id,
            )
            .first()
        )
        if not item:
            return None

        if quantity <= 0:
            self._session.delete(item)
            self._session.commit()
            return None

        item.quantity = quantity
        self._session.commit()
        self._session.refresh(item)
        return item

    def clear(self, cart: Cart) -> None:
        """Vaciar todos los items del carrito."""
        self._session.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
        self._session.commit()
