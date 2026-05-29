"""
Data Transfer Objects — Pydantic schemas.

Validación de entrada/salida desacoplada de los modelos SQLAlchemy.
Preparados para usarse directamente como request/response en FastAPI.
"""

from datetime import date, datetime
from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator

from src.models.user import UserRole
from src.models.menu_item import MenuCategory
from src.models.order import OrderStatus
from src.models.reservation import ReservationStatus


# ════════════════════════════════════════════════════════════
#  USUARIO
# ════════════════════════════════════════════════════════════

VALID_MAJORS = [
    "Ingeniería Mecatrónica y Robótica",
    "Ingeniería Industrial y Manufactura Avanzada",
    "Ingeniería Química",
    "Ingeniería en Ciencias de la Computación Integradas",
]


class ClientRegisterRequest(BaseModel):
    """Schema para registro de cliente (email institucional, sin username)."""

    email: str = Field(
        ..., min_length=5, max_length=255,
        examples=["juan.perez@keyinstitute.edu.sv"],
    )
    password: str = Field(..., min_length=6, max_length=128)
    student_id: str = Field(..., min_length=1, max_length=50, examples=["Key_AB1234"])
    birth_date: date | None = Field(default=None, examples=["2000-05-14"])
    major: str = Field(
        ...,
        description="Carrera universitaria cursada",
        examples=["Ingeniería en Ciencias de la Computación Integradas"],
    )

    @field_validator("major")
    @classmethod
    def validate_major(cls, v: str) -> str:
        if v not in VALID_MAJORS:
            raise ValueError(
                f"Carrera no válida. Debe ser una de: {', '.join(VALID_MAJORS)}"
            )
        return v

    @field_validator("email")
    @classmethod
    def validate_institutional_email(cls, v: str) -> str:
        import re
        email = v.lower().strip()
        if not re.match(r"^[a-záéíóúñü]+\.[a-záéíóúñü]+@keyinstitute\.edu\.sv$", email):
            raise ValueError(
                "El email debe tener el formato nombre.apellido@keyinstitute.edu.sv"
            )
        return email

    @field_validator("student_id")
    @classmethod
    def validate_student_id(cls, v: str) -> str:
        import re
        stripped = v.strip()
        if not re.fullmatch(r"Key_[A-Za-z0-9]{6}", stripped):
            raise ValueError(
                "El carnet debe tener el formato Key_xxxxxx "
                "(Key_ seguido de 6 caracteres alfanuméricos)"
            )
        return stripped

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("La contraseña debe contener al menos una letra mayúscula")
        if not any(c.islower() for c in v):
            raise ValueError("La contraseña debe contener al menos una letra minúscula")
        return v


class UserCreate(BaseModel):
    """Schema para registro de usuario (cliente)."""

    role: UserRole = UserRole.USER
    email: str = Field(
        ..., min_length=5, max_length=255,
        examples=["juan.perez@keyinstitute.edu.sv"],
        description="Email institucional (nombre.apellido@keyinstitute.edu.sv)",
    )
    username: str = Field(..., min_length=3, max_length=100, examples=["juan_perez"])
    password: str = Field(..., min_length=6, max_length=128)
    student_id: str = Field(
        ..., min_length=1, max_length=50,
        examples=["Key_AB1234"],
        description="Carnet universitario único",
    )
    birth_date: date | None = Field(
        default=None,
        examples=["2000-05-14"],
        description="Fecha de nacimiento (YYYY-MM-DD)",
    )
    major: str | None = Field(
        default=None,
        description="Carrera universitaria cursada",
        examples=["Ingeniería en Ciencias de la Computación Integradas"],
    )

    @field_validator("email")
    @classmethod
    def validate_email_by_role(cls, v: str, info) -> str:
        """Email institucional solo para rol USER; admin/staff pueden usar cualquier email."""
        import re
        email = v.lower().strip()
        role = info.data.get("role", UserRole.USER)
        if isinstance(role, str):
            role = UserRole(role)
        if role == UserRole.USER:
            if not re.match(r"^[a-záéíóúñü]+\.[a-záéíóúñü]+@keyinstitute\.edu\.sv$", email):
                raise ValueError(
                    "El email debe tener el formato nombre.apellido@keyinstitute.edu.sv"
                )
        return email

    @field_validator("student_id")
    @classmethod
    def validate_student_id(cls, v: str) -> str:
        """El carnet debe tener el formato Key_xxxxxx (Key_ seguido de exactamente 6 caracteres alfanuméricos)."""
        import re
        stripped = v.strip()
        if not stripped:
            raise ValueError("El carnet universitario no puede estar vacío")
        if not re.fullmatch(r"Key_[A-Za-z0-9]{6}", stripped):
            raise ValueError(
                "El carnet universitario debe tener el formato Key_xxxxxx "
                "(Key_ seguido de exactamente 6 caracteres alfanuméricos, ej: Key_AB1234)"
            )
        return stripped

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """La contraseña debe tener mayúsculas y minúsculas."""
        if not any(c.isupper() for c in v):
            raise ValueError("La contraseña debe contener al menos una letra mayúscula")
        if not any(c.islower() for c in v):
            raise ValueError("La contraseña debe contener al menos una letra minúscula")
        return v

    @field_validator("birth_date")
    @classmethod
    def validate_birth_date(cls, v: date | None) -> date | None:
        """Validar que la fecha de nacimiento sea razonable."""
        if v is None:
            return v
        today = date.today()
        if v > today:
            raise ValueError("La fecha de nacimiento no puede ser en el futuro")
        age = (today - v).days // 365
        if age > 120:
            raise ValueError("La fecha de nacimiento no es válida (edad > 120)")
        return v

    @field_validator("major")
    @classmethod
    def validate_major(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_MAJORS:
            raise ValueError(
                f"Carrera no válida. Debe ser una de: {', '.join(VALID_MAJORS)}"
            )
        return v


class StaffCreate(BaseModel):
    """Schema para registro de staff."""

    full_name: str = Field(..., min_length=3, max_length=200, examples=["María López"])
    password: str = Field(..., min_length=6, max_length=128)
    student_id: str = Field(
        ..., min_length=1, max_length=50,
        examples=["Key_STF001"],
        description="ID presencial asignado al staff",
    )

    @field_validator("student_id")
    @classmethod
    def validate_student_id(cls, v: str) -> str:
        """El ID presencial debe tener el formato Key_xxxxxx."""
        import re
        stripped = v.strip()
        if not stripped:
            raise ValueError("El ID presencial no puede estar vacío")
        if not re.fullmatch(r"Key_[A-Za-z0-9]{6}", stripped):
            raise ValueError(
                "El ID presencial debe tener el formato Key_xxxxxx "
                "(Key_ seguido de exactamente 6 caracteres alfanuméricos, ej: Key_STF001)"
            )
        return stripped

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """La contraseña debe tener mayúsculas y minúsculas."""
        if not any(c.isupper() for c in v):
            raise ValueError("La contraseña debe contener al menos una letra mayúscula")
        if not any(c.islower() for c in v):
            raise ValueError("La contraseña debe contener al menos una letra minúscula")
        return v


StaffRegisterRequest = StaffCreate


class UserLogin(BaseModel):
    """Schema para login."""

    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class UserUpdate(BaseModel):
    """Schema para actualización de usuario."""

    email: str | None = None
    username: str | None = None
    is_active: bool | None = None
    role: UserRole | None = None
    student_id: str | None = None
    birth_date: date | None = None
    major: str | None = None

    @field_validator("major")
    @classmethod
    def validate_major(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_MAJORS:
            raise ValueError(
                f"Carrera no válida. Debe ser una de: {', '.join(VALID_MAJORS)}"
            )
        return v


class ForgotPasswordRequest(BaseModel):
    """Schema para solicitud de recuperación de contraseña."""
    email: str = Field(..., description="Email del usuario")


class ResetPasswordRequest(BaseModel):
    """Schema para restablecer contraseña usando código."""
    email: str = Field(..., description="Email del usuario")
    code: str = Field(..., min_length=6, max_length=6, description="Código de verificación de 6 dígitos")
    new_password: str = Field(..., min_length=6, description="Nueva contraseña")

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """La contraseña debe tener mayúsculas y minúsculas."""
        if not any(c.isupper() for c in v):
            raise ValueError("La contraseña debe contener al menos una letra mayúscula")
        if not any(c.islower() for c in v):
            raise ValueError("La contraseña debe contener al menos una letra minúscula")
        return v


class UserResponse(BaseModel):
    """Schema de respuesta de usuario (sin password)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    student_id: str
    birth_date: date | None
    role: UserRole
    is_active: bool
    sparks: int = 0
    created_at: datetime
    major: str | None = None


# ════════════════════════════════════════════════════════════
#  MENÚ
# ════════════════════════════════════════════════════════════

class MenuItemCreate(BaseModel):
    """Schema para crear item de menú."""

    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    price: float = Field(..., gt=0)
    category: MenuCategory
    image_url: str | None = None
    is_available: bool = True
    is_featured: bool = False
    is_new: bool = False


class MenuItemUpdate(BaseModel):
    """Schema para actualizar item de menú."""

    name: str | None = None
    description: str | None = None
    price: float | None = Field(default=None, gt=0)
    category: MenuCategory | None = None
    image_url: str | None = None
    is_available: bool | None = None
    is_featured: bool | None = None
    is_new: bool | None = None


class MenuItemResponse(BaseModel):
    """Schema de respuesta de item de menú."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    price: float
    category: MenuCategory
    image_url: str | None
    is_available: bool
    is_featured: bool
    is_new: bool
    created_at: datetime


# ════════════════════════════════════════════════════════════
#  CARRITO
# ════════════════════════════════════════════════════════════

class CartItemAdd(BaseModel):
    """Schema para agregar item al carrito."""

    menu_item_id: int = Field(..., gt=0)
    quantity: int = Field(default=1, gt=0)


class CartItemUpdate(BaseModel):
    """Schema para actualizar cantidad en carrito."""

    menu_item_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)


# ════════════════════════════════════════════════════════════
#  ORDEN
# ════════════════════════════════════════════════════════════

class OrderCreate(BaseModel):
    """Schema para crear orden (desde carrito)."""

    notes: str | None = None
    scheduled_time: datetime | None = None  # Para pedidos diferidos


class ScheduleSlotResponse(BaseModel):
    """Franja horaria con disponibilidad de pedidos programados."""

    start: datetime
    label: str
    count: int
    remaining: int
    full: bool


class OrderResponse(BaseModel):
    """Schema de respuesta de orden."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    total_price: float
    status: OrderStatus
    notes: str | None
    scheduled_time: datetime | None
    created_at: datetime


# ════════════════════════════════════════════════════════════
#  RESERVA
# ════════════════════════════════════════════════════════════

class ReservationCreate(BaseModel):
    """Schema para crear reserva."""

    scheduled_time: datetime
    people_count: int = Field(..., gt=0, le=20)
    notes: str | None = None


class ReservationResponse(BaseModel):
    """Schema de respuesta de reserva."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    scheduled_time: datetime
    people_count: int
    status: ReservationStatus
    notes: str | None
    created_at: datetime


# ════════════════════════════════════════════════════════════
#  PROMOCIONES
# ════════════════════════════════════════════════════════════

class PromotionResponse(BaseModel):
    """Respuesta de promoción activa para un usuario."""

    is_birthday: bool = False
    discount_percent: float = 0.0
    message: str = ""


class RankingItemResponse(BaseModel):
    """Item dentro de un ranking."""

    model_config = ConfigDict(from_attributes=True)

    menu_item_id: int
    name: str
    category: str
    total_sold: int
    price: float
