from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Artwork(Base):
    __tablename__ = "artworks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(50), index=True)
    pid: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(String(500), default="")
    author: Mapped[str] = mapped_column(String(255), default="")
    author_id: Mapped[str] = mapped_column(String(255), default="")
    source_url: Mapped[str] = mapped_column(String(2048), default="")

    # Image metadata
    page_count: Mapped[int] = mapped_column(Integer, default=1)
    width: Mapped[int] = mapped_column(Integer, default=0)
    height: Mapped[int] = mapped_column(Integer, default=0)
    is_nsfw: Mapped[bool] = mapped_column(Boolean, default=False)
    is_ai: Mapped[bool] = mapped_column(Boolean, default=False)

    # Storage
    images_json: Mapped[str] = mapped_column(Text, default="[]")

    # Raw metadata from platform
    raw_info: Mapped[str] = mapped_column(Text, default="{}")

    # Telegram compatibility
    telegram_file_id_thumb: Mapped[str] = mapped_column(String(255), default="")
    telegram_file_id_original: Mapped[str] = mapped_column(String(255), default="")
    telegram_message_link: Mapped[str] = mapped_column(String(500), default="")

    # Posting metadata
    posted_by: Mapped[str] = mapped_column(String(255), default="")
    post_count: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    tags: Mapped[list["ArtworkTag"]] = relationship(back_populates="artwork", cascade="all, delete")


class ArtworkTag(Base):
    __tablename__ = "artwork_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    artwork_id: Mapped[int] = mapped_column(ForeignKey("artworks.id", ondelete="CASCADE"))
    tag: Mapped[str] = mapped_column(String(255), index=True)

    artwork: Mapped["Artwork"] = relationship(back_populates="tags")
