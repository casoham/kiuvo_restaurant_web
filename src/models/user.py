"""
Modelo de Usuario con soporte de roles.

Incluye carnet universitario (student_id) y fecha de nacimiento
para el sistema de descuentos por cumpleaños.
"""

import enum
from datetime import date, datetime, timezone

from sqlalchemy import Date, String, Boolean, Enum, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.database import Base


class UserRole(str, enum.Enum):
    """Roles disponibles en el sistema."""

    ADMIN = "admin"
    STAFF = "staff"
    USER = "user"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    username: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            values_callable=lambda e: [i.value for i in e],
            create_type=False,
        ),
        default=UserRole.USER,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── Campos universitarios ────────────────────────────────
    student_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True,
        doc="Carnet universitario único del estudiante",
    )
    birth_date: Mapped[date | None] = mapped_column(
        Date, nullable=True,
        doc="Fecha de nacimiento para descuento de cumpleaños",
    )
    major: Mapped[str | None] = mapped_column(
        String(150), nullable=True,
        doc="Carrera universitaria elegida",
    )

    # ── Sparks (puntos de fidelidad) ────────────────────────
    sparks: Mapped[int] = mapped_column(
        default=0, nullable=False, server_default="0",
        doc="Sparks acumulados por compras entregadas",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relaciones ──────────────────────────────────────────
    orders: Mapped[list["Order"]] = relationship(  # noqa: F821
        "Order", back_populates="user", cascade="all, delete-orphan"
    )
    cart: Mapped["Cart"] = relationship(  # noqa: F821
        "Cart", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    reservations: Mapped[list["Reservation"]] = relationship(  # noqa: F821
        "Reservation", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<User(id={self.id}, username={self.username!r}, "
            f"student_id={self.student_id!r}, role={self.role.value})>"
        )
