from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BotPostQueue(Base):
    __tablename__ = "bot_post_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    artwork_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("artworks.id", ondelete="CASCADE"), index=True
    )
    platform: Mapped[str] = mapped_column(String(50), default="telegram")
    channel_id: Mapped[str] = mapped_column(String(255), default="")  # 空 = resolve_channel()
    priority: Mapped[int] = mapped_column(Integer, default=100, index=True)  # 越小越优先
    status: Mapped[str] = mapped_column(
        String(50), default="pending", index=True
    )  # pending / processing / done / failed
    added_by: Mapped[str] = mapped_column(String(255), default="")
    added_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    artwork: Mapped[Artwork] = relationship(back_populates="queue_items")  # type: ignore[name-defined]
    added_by_user: Mapped[User | None] = relationship(
        foreign_keys="[BotPostQueue.added_by_user_id]"
    )  # type: ignore[name-defined]


class BotChannel(Base):
    __tablename__ = "bot_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(50), default="telegram")
    channel_id: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255), default="")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    conditions: Mapped[str] = mapped_column(Text, default="{}")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BotSetting(Base):
    __tablename__ = "bot_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    value: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(String(500), default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
