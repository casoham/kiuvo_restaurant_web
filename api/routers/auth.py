"""
Router de Autenticación.

Endpoints: registro, login, refresh token, cambio de contraseña.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from api.dependencies import DBSession, CurrentUser, AdminUser
from src.services.auth_service import AuthService
from src.dto.schemas import (
    UserCreate,
    UserResponse,
    ClientRegisterRequest,
    StaffRegisterRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from src.services.password_reset_service import PasswordResetService
from src.utils.jwt import create_access_token, create_refresh_token, decode_token
from src.utils.exceptions import AuthenticationError, ValidationError
from src.utils.logger import logger

router = APIRouter(prefix="/auth", tags=["Autenticación"])


# ── Schemas específicos de la API ───────────────────────────

class TokenResponse(BaseModel):
    """Respuesta con tokens JWT."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Solicitud de refresh token."""
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """Solicitud de cambio de contraseña."""
    current_password: str
    new_password: str


class MessageResponse(BaseModel):
    """Respuesta genérica con mensaje."""
    message: str


# ── Endpoints ───────────────────────────────────────────────

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo usuario",
)
def register(data: UserCreate, db: DBSession):
    """Crear una nueva cuenta de usuario."""
    auth_service = AuthService(db)
    user = auth_service.register(
        email=data.email,
        username=data.username,
        password=data.password,
        student_id=data.student_id,
        birth_date=data.birth_date,
        role=data.role,
        major=data.major,
    )
    return user


@router.post(
    "/register/client",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar cliente (email institucional)",
)
def register_client(data: ClientRegisterRequest, db: DBSession):
    """Registrar cliente con email @keyinstitute.edu.sv y carnet Key_xxxxxx."""
    auth_service = AuthService(db)
    user = auth_service.register_client(
        email=data.email,
        password=data.password,
        student_id=data.student_id,
        birth_date=data.birth_date,
        major=data.major,
    )
    return user


@router.post(
    "/register/staff",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar staff",
)
def register_staff(data: StaffRegisterRequest, db: DBSession, current_user: AdminUser):
    """Registrar miembro de staff con ID presencial Key_xxxxxx."""
    auth_service = AuthService(db)
    user = auth_service.register_staff(
        full_name=data.full_name,
        password=data.password,
        student_id=data.student_id,
    )
    return user


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Solicitar recuperación de contraseña",
)
def forgot_password(body: ForgotPasswordRequest, db: DBSession):
    """Genera y envía (o registra en logs) un código de 6 dígitos."""
    auth_service = AuthService(db)
    from src.repositories.user_repository import UserRepository

    email = body.email.lower().strip()
    user = UserRepository(db).get_by_email(email)
    if user is None:
        # Respuesta genérica para no revelar si el email existe
        return MessageResponse(
            message="Si el email existe, recibirás un código de verificación."
        )

    reset_svc = PasswordResetService()
    code = reset_svc.generate_code(email)
    sent = reset_svc.send_code(email, code)
    if not sent:
        logger.warning(f"[DEV] Código de recuperación para {email}: {code}")

    return MessageResponse(
        message="Si el email existe, recibirás un código de verificación."
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Restablecer contraseña con código",
)
def reset_password(body: ResetPasswordRequest, db: DBSession):
    """Verifica el código y actualiza la contraseña."""
    reset_svc = PasswordResetService()
    if not reset_svc.verify_code(body.email, body.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido o expirado",
        )

    auth_service = AuthService(db)
    try:
        auth_service.change_password_by_email(body.email, body.new_password)
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró un usuario con ese email",
        )
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.message)

    return MessageResponse(message="Contraseña restablecida exitosamente")


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesión",
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: DBSession = None,
):
    """
    Autenticar con username/password y obtener tokens JWT.

    Compatible con OAuth2 password flow (Swagger UI).
    """
    auth_service = AuthService(db)
    user = auth_service.login(form_data.username, form_data.password)

    access_token = create_access_token(user.id, user.role.value)
    refresh_token = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Renovar tokens",
)
def refresh_tokens(body: RefreshRequest, db: DBSession):
    """Obtener nuevos tokens usando un refresh token válido."""
    try:
        payload = decode_token(body.refresh_token)
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido o expirado",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere un refresh token",
        )

    user_id = int(payload["sub"])

    # Verificar que el usuario siga existiendo y activo
    from src.repositories.user_repository import UserRepository
    user_repo = UserRepository(db)
    user = user_repo.get(user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no válido",
        )

    access_token = create_access_token(user.id, user.role.value)
    refresh_token = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Cambiar contraseña",
)
def change_password(
    body: ChangePasswordRequest,
    current_user: CurrentUser,
    db: DBSession,
):
    """Cambiar la contraseña del usuario autenticado."""
    auth_service = AuthService(db)
    auth_service.change_password(
        user=current_user,
        old_password=body.current_password,
        new_password=body.new_password,
    )
    return MessageResponse(message="Contraseña actualizada exitosamente")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Perfil del usuario actual",
)
def get_me(current_user: CurrentUser):
    """Obtener datos del usuario autenticado."""
    return current_user
