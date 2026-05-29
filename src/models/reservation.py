"""
Modelo de Reserva.
"""

import enum
from datetime import datetime, timezone

from sqlalchemy import Integer, ForeignKey, Enum, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.database import Base


class ReservationStatus(str, enum.Enum):
    """Estados de una reserva."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scheduled_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    people_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ReservationStatus] = mapped_column(
        Enum(
            ReservationStatus,
            name="reservation_status",
            values_callable=lambda e: [i.value for i in e],
            create_type=False,
        ),
        default=ReservationStatus.PENDING,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relaciones ──────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="reservations")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<Reservation(id={self.id}, user_id={self.user_id}, "
            f"people={self.people_count}, status={self.status.value})>"
        )
