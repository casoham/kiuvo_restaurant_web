"""
Router de Carrito de Compras.

Cada usuario tiene un carrito individual.
"""

from fastapi import APIRouter, status
from pydantic import BaseModel

from api.dependencies import DBSession, CurrentUser
from src.services.cart_service import CartService
from src.dto.schemas import CartItemAdd, CartItemUpdate

router = APIRouter(prefix="/cart", tags=["Carrito"])


# ── Schemas de respuesta ────────────────────────────────────

class CartSummaryItem(BaseModel):
    """Item del resumen del carrito."""
    menu_item_id: int
    name: str
    unit_price: float
    quantity: int
    subtotal: float


class CartResponse(BaseModel):
    """Respuesta completa del carrito."""
    items: list[CartSummaryItem]
    item_count: int
    total: float


class MessageResponse(BaseModel):
    message: str


# ── Endpoints ───────────────────────────────────────────────

@router.get(
    "/",
    response_model=CartResponse,
    summary="Ver mi carrito",
)
def get_cart(db: DBSession, current_user: CurrentUser):
    """Obtener el contenido del carrito del usuario actual."""
    cart_service = CartService(db)
    summary = cart_service.get_cart_summary(current_user.id)
    total = cart_service.get_total(current_user.id)
    item_count = cart_service.get_item_count(current_user.id)

    items = [
        CartSummaryItem(
            menu_item_id=item["menu_item_id"],
            name=item["name"],
            unit_price=item["price"],
            quantity=item["quantity"],
            subtotal=item["subtotal"],
        )
        for item in summary
    ]

    return CartResponse(items=items, item_count=item_count, total=total)


@router.post(
    "/items",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar item al carrito",
)
def add_item(data: CartItemAdd, db: DBSession, current_user: CurrentUser):
    """Agregar un item del menú al carrito."""
    cart_service = CartService(db)
    cart_service.add_item(current_user.id, data.menu_item_id, data.quantity)
    return MessageResponse(message="Item agregado al carrito")


@router.put(
    "/items",
    response_model=MessageResponse,
    summary="Actualizar cantidad de item",
)
def update_item(data: CartItemUpdate, db: DBSession, current_user: CurrentUser):
    """Actualizar la cantidad de un item en el carrito."""
    cart_service = CartService(db)
    cart_service.update_quantity(current_user.id, data.menu_item_id, data.quantity)
    return MessageResponse(message="Cantidad actualizada")


@router.delete(
    "/items/{menu_item_id}",
    response_model=MessageResponse,
    summary="Remover item del carrito",
)
def remove_item(menu_item_id: int, db: DBSession, current_user: CurrentUser):
    """Eliminar un item del carrito."""
    cart_service = CartService(db)
    cart_service.remove_item(current_user.id, menu_item_id)
    return MessageResponse(message="Item removido del carrito")


@router.delete(
    "/",
    response_model=MessageResponse,
    summary="Vaciar carrito",
)
def clear_cart(db: DBSession, current_user: CurrentUser):
    """Vaciar completamente el carrito del usuario."""
    cart_service = CartService(db)
    cart_service.clear_cart(current_user.id)
    return MessageResponse(message="Carrito vaciado")
