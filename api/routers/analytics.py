"""
Router de Analytics / Rankings.

Estadísticas de ventas, productos populares, tendencias.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from api.dependencies import DBSession, StaffUser
from src.services.analytics_service import AnalyticsService
from src.dto.schemas import RankingItemResponse

router = APIRouter(prefix="/analytics", tags=["Analytics"])


class AnalyticsSummary(BaseModel):
    """Resumen general de analíticas."""
    total_orders: int
    total_revenue: float


@router.get(
    "/summary",
    response_model=AnalyticsSummary,
    summary="Resumen general",
)
def get_summary(db: DBSession, staff: StaffUser):
    """Resumen de total de órdenes e ingresos (staff/admin)."""
    analytics = AnalyticsService(db)
    return AnalyticsSummary(
        total_orders=analytics.get_total_orders_count(),
        total_revenue=analytics.get_total_revenue(),
    )


@router.get(
    "/popular",
    response_model=list[RankingItemResponse],
    summary="Productos más vendidos",
)
def get_popular(db: DBSession, staff: StaffUser, limit: int = 10):
    """Ranking de productos más vendidos (staff/admin)."""
    analytics = AnalyticsService(db)
    items = analytics.get_most_popular_items(limit=limit)
    return [RankingItemResponse(**item) for item in items]


@router.get(
    "/trending",
    response_model=list[RankingItemResponse],
    summary="Productos tendencia",
)
def get_trending(db: DBSession, staff: StaffUser, limit: int = 10, days: int = 7):
    """Productos en tendencia (últimos N días) — staff/admin."""
    analytics = AnalyticsService(db)
    items = analytics.get_trending_items(limit=limit, days=days)
    return [RankingItemResponse(**item) for item in items]


@router.get(
    "/revenue",
    response_model=list[RankingItemResponse],
    summary="Productos por ingresos",
)
def get_revenue(db: DBSession, staff: StaffUser, limit: int = 10):
    """Ranking de productos por ingresos generados (staff/admin)."""
    analytics = AnalyticsService(db)
    items = analytics.get_top_revenue_items(limit=limit)
    return [RankingItemResponse(**item) for item in items]
