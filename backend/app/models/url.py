import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class URL(Base):
    """
    Primary key `id` is a BIGSERIAL — its sequence value is what gets
    base62-encoded into `short_code` (see ARCHITECTURE.md section 9.1).
    `short_code` is nullable for the brief instant between INSERT and the
    follow-up UPDATE that sets it within the same transaction (see
    URLRepository.create) — it is otherwise always populated.
    """

    __tablename__ = "urls"
    __table_args__ = (
        Index("ix_urls_owner_created", "owner_id", "created_at"),
        Index(
            "ix_urls_expires_at_active",
            "expires_at",
            postgresql_where="expires_at IS NOT NULL",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    short_code: Mapped[str | None] = mapped_column(String(16), unique=True, index=True)
    custom_alias: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    target_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Denormalized counter for fast dashboard sorts ("top URLs") without
    # always hitting click_events; kept eventually-consistent by the worker.
    total_clicks: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    owner = relationship("User", back_populates="urls")
    click_events = relationship("ClickEvent", back_populates="url", cascade="all, delete-orphan")
    daily_stats = relationship("URLDailyStat", back_populates="url", cascade="all, delete-orphan")

    @property
    def effective_code(self) -> str:
        """The code actually used in the public short URL."""
        return self.custom_alias or self.short_code
