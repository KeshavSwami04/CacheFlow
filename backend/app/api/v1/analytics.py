from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db_read
from app.models.user import User
from app.schemas.analytics import URLAnalyticsResponse, UserAnalyticsSummary
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=UserAnalyticsSummary)
async def my_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_read),
):
    return await AnalyticsService(db).user_summary(current_user.id)


@router.get("/urls/{url_id}", response_model=URLAnalyticsResponse)
async def url_analytics(
    url_id: int,
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_read),
):
    return await AnalyticsService(db).url_analytics(current_user.id, url_id, days)
