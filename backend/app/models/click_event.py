from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ClickEvent(Base):
    """
    Raw, immutable click log — one row per redirect, written by the
    worker (never by the redirect endpoint directly; see Architecture
    section 4). Append-only, so no updates/locks contend with the hot
    redirect path.
    """

    __tablename__ = "click_events"
    __table_args__ = (
        Index("ix_click_events_url_clicked", "url_id", "clicked_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    url_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("urls.id", ondelete="CASCADE"), nullable=False
    )
    clicked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    referrer: Mapped[str | None] = mapped_column(String(512), nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    device_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Privacy: we never persist the raw IP, only a salted hash — enough to
    # rate-limit / dedupe, not enough to identify a visitor.
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    url = relationship("URL", back_populates="click_events")


class URLDailyStat(Base):
    """
    Pre-aggregated daily rollup so the dashboard's click-over-time chart
    is an indexed point lookup instead of a scan/aggregate over
    click_events. Upserted by the worker on every processed event.
    """

    __tablename__ = "url_daily_stats"

    url_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("urls.id", ondelete="CASCADE"), primary_key=True
    )
    stat_date: Mapped[date] = mapped_column(Date, primary_key=True)
    click_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    referrer_breakdown: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    country_breakdown: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    url = relationship("URL", back_populates="daily_stats")
