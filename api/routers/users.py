"""
Router de Usuarios.

CRUD de usuarios — acceso restringido por roles.
"""

from fastapi import APIRouter, status
from pydantic import BaseModel

from api.dependencies import DBSession, CurrentUser, AdminUser
from src.services.user_service import UserService
from src.dto.schemas import UserResponse, UserUpdate
from src.models.user import UserRole

router = APIRouter(prefix="/users", tags=["Usuarios"])


class MessageResponse(BaseModel):
    message: str


@router.get(
    "/",
    response_model=list[UserResponse],
    summary="Listar todos los usuarios",
)
def list_users(db: DBSession, admin: AdminUser, skip: int = 0, limit: int = 100):
    """Listar usuarios (solo admin)."""
    user_service = UserService(db)
    return user_service.get_all(skip=skip, limit=limit)


@router.get(
    "/by-role/{role}",
    response_model=list[UserResponse],
    summary="Listar usuarios por rol",
)
def list_by_role(role: UserRole, db: DBSession, admin: AdminUser):
    """Filtrar usuarios por rol (solo admin)."""
    user_service = UserService(db)
    return user_service.get_by_role(role)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Obtener usuario por ID",
)
def get_user(user_id: int, db: DBSession, admin: AdminUser):
    """Obtener detalles de un usuario (solo admin)."""
    user_service = UserService(db)
    return user_service.get_by_id(user_id)


@router.put(
    "/profile",
    response_model=UserResponse,
    summary="Actualizar mi perfil",
)
def update_profile(data: UserUpdate, db: DBSession, current_user: CurrentUser):
    """
    Actualizar el perfil del usuario autenticado.

    Nota: los campos `role` e `is_active` son ignorados para
    usuarios no-admin (se requiere endpoint admin).
    """
    user_service = UserService(db)
    update_data = data.model_dump(exclude_unset=True)

    # Usuarios normales no pueden cambiar su propio rol ni activarse/desactivarse
    if current_user.role != UserRole.ADMIN:
        update_data.pop("role", None)
        update_data.pop("is_active", None)

    return user_service.update_profile(current_user, update_data)


@router.put(
    "/{user_id}/role",
    response_model=UserResponse,
    summary="Cambiar rol de usuario",
)
def change_role(user_id: int, role: UserRole, db: DBSession, admin: AdminUser):
    """Cambiar el rol de un usuario (solo admin)."""
    user_service = UserService(db)
    return user_service.change_role(admin, user_id, role)


@router.put(
    "/{user_id}/deactivate",
    response_model=UserResponse,
    summary="Desactivar usuario",
)
def deactivate_user(user_id: int, db: DBSession, admin: AdminUser):
    """Desactivar una cuenta de usuario (solo admin)."""
    user_service = UserService(db)
    return user_service.deactivate_user(admin, user_id)


@router.put(
    "/{user_id}/activate",
    response_model=UserResponse,
    summary="Activar usuario",
)
def activate_user(user_id: int, db: DBSession, admin: AdminUser):
    """Reactivar una cuenta de usuario (solo admin)."""
    user_service = UserService(db)
    return user_service.activate_user(admin, user_id)


@router.delete(
    "/{user_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Eliminar usuario",
)
def delete_user(user_id: int, db: DBSession, admin: AdminUser):
    """Eliminar un usuario permanentemente (solo admin)."""
    user_service = UserService(db)
    user_service.delete_user(admin, user_id)
    return MessageResponse(message=f"Usuario {user_id} eliminado exitosamente")
