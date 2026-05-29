"""
Router de Órdenes / Pedidos.

Ciclo completo: crear desde carrito, consultar, cambiar estado, cancelar.

NOTA: Las rutas fijas (mine, active, status/) van ANTES de /{order_id}
para evitar que FastAPI las capture como parámetros enteros.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from api.dependencies import DBSession, CurrentUser, StaffUser
from src.services.order_service import OrderService
from src.services.promotion_service import PromotionService
from datetime import datetime, timezone

from src.dto.schemas import (
    OrderCreate,
    OrderResponse,
    PromotionResponse,
    ScheduleSlotResponse,
)
from src.models.order import OrderStatus
from src.models.user import UserRole

router = APIRouter(prefix="/orders", tags=["Órdenes"])


class OrderDetailResponse(OrderResponse):
    """Orden con detalle de items."""
    items: list[dict] = []


class StatusUpdateRequest(BaseModel):
    """Solicitud de cambio de estado."""
    status: OrderStatus


class MessageResponse(BaseModel):
    message: str


# ── Helpers ─────────────────────────────────────────────────

def _order_to_detail(order) -> dict:
    """Convertir orden ORM a dict con items."""
    data = {
        "id": order.id,
        "user_id": order.user_id,
        "total_price": order.total_price,
        "status": order.status,
        "notes": order.notes,
        "scheduled_time": order.scheduled_time,
        "created_at": order.created_at,
        "items": [],
    }
    if hasattr(order, "items") and order.items:
        data["items"] = [
            {
                "menu_item_id": item.menu_item_id,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "name": item.menu_item.name if item.menu_item else "Desconocido",
            }
            for item in order.items
        ]
    return data


# ══════════════════════════════════════════════════════════
#  Rutas FIJAS primero (antes de /{order_id})
# ══════════════════════════════════════════════════════════

@router.get(
    "/slots",
    response_model=list[ScheduleSlotResponse],
    summary="Disponibilidad de franjas horarias",
)
def get_schedule_slots(
    db: DBSession,
    current_user: CurrentUser,
    hours_ahead: int = 8,
    slot_minutes: int = 15,
):
    """Consultar cupo por franja de 15 min (6:00–17:00)."""
    order_service = OrderService(db)
    base = datetime.now(timezone.utc)
    slots = order_service.get_schedule_slots(
        base_date=base,
        hours_ahead=hours_ahead,
        slot_minutes=slot_minutes,
    )
    return [ScheduleSlotResponse(**s) for s in slots]


@router.get(
    "/my-promotion",
    response_model=PromotionResponse,
    summary="Ver mi promoción activa",
)
def get_my_promotion(current_user: CurrentUser):
    """Verificar si el usuario tiene una promoción activa (cumpleaños)."""
    info = PromotionService.get_promotion_info(current_user)
    return PromotionResponse(**info)


@router.get(
    "/mine",
    response_model=list[OrderResponse],
    summary="Mis órdenes",
)
def get_my_orders(db: DBSession, current_user: CurrentUser):
    """Obtener el historial de órdenes del usuario autenticado."""
    order_service = OrderService(db)
    return order_service.get_user_orders(current_user.id)


@router.get(
    "/active",
    response_model=list[OrderResponse],
    summary="Órdenes activas",
)
def list_active_orders(db: DBSession, staff: StaffUser):
    """Listar órdenes activas — no entregadas ni canceladas (staff/admin)."""
    order_service = OrderService(db)
    return order_service.get_active_orders()


@router.get(
    "/status/{order_status}",
    response_model=list[OrderResponse],
    summary="Órdenes por estado",
)
def list_by_status(order_status: OrderStatus, db: DBSession, staff: StaffUser):
    """Filtrar órdenes por estado (staff/admin)."""
    order_service = OrderService(db)
    return order_service.get_by_status(order_status)


# ══════════════════════════════════════════════════════════
#  Ruta raíz y creación
# ══════════════════════════════════════════════════════════

@router.get(
    "/",
    response_model=list[OrderResponse],
    summary="Listar todas las órdenes",
)
def list_all_orders(
    db: DBSession,
    staff: StaffUser,
    skip: int = 0,
    limit: int = 100,
):
    """Listar todas las órdenes (staff/admin)."""
    order_service = OrderService(db)
    return order_service.get_all_orders(skip=skip, limit=limit)


@router.post(
    "/",
    response_model=OrderDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear orden desde carrito",
)
def create_order(data: OrderCreate, db: DBSession, current_user: CurrentUser):
    """
    Crear una orden con los items del carrito actual.

    Si es el cumpleaños del usuario, se aplica descuento automático del 20%.
    """
    order_service = OrderService(db)
    order = order_service.create_from_cart(
        user=current_user,
        notes=data.notes,
        scheduled_time=data.scheduled_time,
    )
    return _order_to_detail(order)


# ══════════════════════════════════════════════════════════
#  Rutas con /{order_id} al final
# ══════════════════════════════════════════════════════════

@router.get(
    "/{order_id}",
    response_model=OrderDetailResponse,
    summary="Detalle de orden",
)
def get_order(order_id: int, db: DBSession, current_user: CurrentUser):
    """
    Obtener detalle de una orden.

    Usuarios normales solo pueden ver sus propias órdenes.
    Staff/admin pueden ver cualquiera.
    """
    order_service = OrderService(db)
    order = order_service.get_by_id(order_id)

    if current_user.role == UserRole.USER and order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes ver órdenes de otros usuarios",
        )

    return _order_to_detail(order)


@router.post(
    "/{order_id}/cancel",
    response_model=OrderResponse,
    summary="Cancelar mi orden",
)
def cancel_order(order_id: int, db: DBSession, current_user: CurrentUser):
    """Cancelar una orden propia (si el estado lo permite)."""
    order_service = OrderService(db)
    return order_service.cancel_order(current_user, order_id)


@router.put(
    "/{order_id}/status",
    response_model=OrderResponse,
    summary="Cambiar estado de orden",
)
def update_status(
    order_id: int,
    body: StatusUpdateRequest,
    db: DBSession,
    staff: StaffUser,
):
    """Cambiar el estado de una orden (staff/admin)."""
    order_service = OrderService(db)
    return order_service.update_status(staff, order_id, body.status)
