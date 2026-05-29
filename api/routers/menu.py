"""
Router de Menú.

Endpoints públicos de consulta + CRUD restringido para admin/staff.
"""

from fastapi import APIRouter, status
from pydantic import BaseModel

from api.dependencies import DBSession, CurrentUser, StaffUser
from src.services.menu_service import MenuService
from src.dto.schemas import MenuItemCreate, MenuItemUpdate, MenuItemResponse
from src.models.menu_item import MenuCategory

router = APIRouter(prefix="/menu", tags=["Menú"])


class MessageResponse(BaseModel):
    message: str


# ── Lectura (público con token) ─────────────────────────────

@router.get(
    "/",
    response_model=list[MenuItemResponse],
    summary="Listar items disponibles",
)
def list_available(db: DBSession, current_user: CurrentUser):
    """Obtener todos los items de menú disponibles."""
    menu_service = MenuService(db)
    return menu_service.get_available()


@router.get(
    "/all",
    response_model=list[MenuItemResponse],
    summary="Listar TODOS los items (incluye no disponibles)",
)
def list_all(db: DBSession, staff: StaffUser):
    """Listar todos los items incluyendo no disponibles (staff/admin)."""
    menu_service = MenuService(db)
    return menu_service.get_all()


@router.get(
    "/featured",
    response_model=list[MenuItemResponse],
    summary="Items destacados",
)
def list_featured(db: DBSession, current_user: CurrentUser):
    """Obtener items marcados como destacados."""
    menu_service = MenuService(db)
    return menu_service.get_featured()


@router.get(
    "/new",
    response_model=list[MenuItemResponse],
    summary="Items nuevos",
)
def list_new(db: DBSession, current_user: CurrentUser):
    """Obtener items marcados como nuevos."""
    menu_service = MenuService(db)
    return menu_service.get_new_items()


@router.get(
    "/category/{category}",
    response_model=list[MenuItemResponse],
    summary="Items por categoría",
)
def list_by_category(category: MenuCategory, db: DBSession, current_user: CurrentUser):
    """Filtrar items de menú por categoría."""
    menu_service = MenuService(db)
    return menu_service.get_by_category(category)


@router.get(
    "/search",
    response_model=list[MenuItemResponse],
    summary="Buscar items",
)
def search_items(q: str, db: DBSession, current_user: CurrentUser):
    """Buscar items por nombre o descripción."""
    menu_service = MenuService(db)
    return menu_service.search(q)


@router.get(
    "/{item_id}",
    response_model=MenuItemResponse,
    summary="Detalle de item",
)
def get_item(item_id: int, db: DBSession, current_user: CurrentUser):
    """Obtener detalle de un item de menú por ID."""
    menu_service = MenuService(db)
    return menu_service.get_by_id(item_id)


# ── Escritura (staff/admin) ─────────────────────────────────

@router.post(
    "/",
    response_model=MenuItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear item de menú",
)
def create_item(data: MenuItemCreate, db: DBSession, staff: StaffUser):
    """Crear un nuevo item de menú (staff/admin)."""
    menu_service = MenuService(db)
    return menu_service.create_item(staff, data.model_dump())


@router.put(
    "/{item_id}",
    response_model=MenuItemResponse,
    summary="Actualizar item de menú",
)
def update_item(item_id: int, data: MenuItemUpdate, db: DBSession, staff: StaffUser):
    """Actualizar un item de menú existente (staff/admin)."""
    menu_service = MenuService(db)
    return menu_service.update_item(staff, item_id, data.model_dump(exclude_unset=True))


@router.patch(
    "/{item_id}/toggle-availability",
    response_model=MenuItemResponse,
    summary="Alternar disponibilidad",
)
def toggle_availability(item_id: int, db: DBSession, staff: StaffUser):
    """Alternar la disponibilidad de un item (staff/admin)."""
    menu_service = MenuService(db)
    return menu_service.toggle_availability(staff, item_id)


@router.patch(
    "/{item_id}/toggle-featured",
    response_model=MenuItemResponse,
    summary="Alternar item destacado",
)
def toggle_featured(item_id: int, db: DBSession, staff: StaffUser):
    """Alternar si un item es destacado (staff/admin)."""
    menu_service = MenuService(db)
    return menu_service.toggle_featured(staff, item_id)


@router.patch(
    "/{item_id}/toggle-new",
    response_model=MenuItemResponse,
    summary="Alternar item nuevo/temporada",
)
def toggle_new(item_id: int, db: DBSession, staff: StaffUser):
    """Alternar si un item se muestra como novedad/promoción (staff/admin)."""
    menu_service = MenuService(db)
    return menu_service.toggle_new(staff, item_id)


@router.delete(
    "/{item_id}",
    response_model=MessageResponse,
    summary="Eliminar item de menú",
)
def delete_item(item_id: int, db: DBSession, staff: StaffUser):
    """Eliminar un item de menú (staff/admin)."""
    menu_service = MenuService(db)
    menu_service.delete_item(staff, item_id)
    return MessageResponse(message=f"Item {item_id} eliminado exitosamente")
