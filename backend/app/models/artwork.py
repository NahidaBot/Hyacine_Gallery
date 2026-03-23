from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.author import Author
    from app.models.user import User


class Artwork(Base):
    __tablename__ = "artworks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # 从主要来源冗余存储，便于过滤、展示和机器人路由
    platform: Mapped[str] = mapped_column(String(50), index=True)
    pid: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(String(500), default="")
    title_zh: Mapped[str] = mapped_column(String(500), default="")
    author: Mapped[str] = mapped_column(String(255), default="")
    author_id: Mapped[str] = mapped_column(String(255), default="")
    source_url: Mapped[str] = mapped_column(String(2048), default="")
    page_count: Mapped[int] = mapped_column(Integer, default=1)
    is_nsfw: Mapped[bool] = mapped_column(Boolean, default=False)
    is_ai: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    images: Mapped[list[ArtworkImage]] = relationship(
        back_populates="artwork", cascade="all, delete-orphan", order_by="ArtworkImage.page_index"
    )
    tags: Mapped[list[Tag]] = relationship(secondary="artwork_tags", back_populates="artworks")
    author_ref_id: Mapped[int | None] = mapped_column(
        ForeignKey("authors.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # 记录通过管理面板导入该作品的用户
    imported_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    author_ref: Mapped[Author | None] = relationship(back_populates="artworks")  # noqa: F821
    imported_by: Mapped[User | None] = relationship(foreign_keys="[Artwork.imported_by_id]")  # noqa: F821
    sources: Mapped[list[ArtworkSource]] = relationship(
        back_populates="artwork", cascade="all, delete-orphan"
    )
    post_logs: Mapped[list[BotPostLog]] = relationship(
        back_populates="artwork", cascade="all, delete-orphan"
    )
    queue_items: Mapped[list[BotPostQueue]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="artwork", cascade="all, delete-orphan"
    )


class ArtworkImage(Base):
    __tablename__ = "artwork_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    artwork_id: Mapped[int] = mapped_column(ForeignKey("artworks.id", ondelete="CASCADE"))
    page_index: Mapped[int] = mapped_column(Integer, default=0)
    url_original: Mapped[str] = mapped_column(String(2048), default="")
    url_thumb: Mapped[str] = mapped_column(String(2048), default="")
    width: Mapped[int] = mapped_column(Integer, default=0)
    height: Mapped[int] = mapped_column(Integer, default=0)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    file_name: Mapped[str] = mapped_column(String(500), default="")
    storage_path: Mapped[str] = mapped_column(String(1024), default="")
    telegram_file_id: Mapped[str] = mapped_column(String(255), default="")
    phash: Mapped[str] = mapped_column(String(16), default="", index=True)
    url_raw: Mapped[str] = mapped_column(String(2048), default="")
    storage_path_raw: Mapped[str] = mapped_column(String(1024), default="")
    raw_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    artwork: Mapped[Artwork] = relationship(back_populates="images")


class ArtworkSource(Base):
    __tablename__ = "artwork_sources"
    __table_args__ = (UniqueConstraint("platform", "pid", name="uq_sources_platform_pid"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    artwork_id: Mapped[int] = mapped_column(
        ForeignKey("artworks.id", ondelete="CASCADE"), index=True
    )
    platform: Mapped[str] = mapped_column(String(50), index=True)
    pid: Mapped[str] = mapped_column(String(255))
    source_url: Mapped[str] = mapped_column(String(2048), default="")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_info: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    artwork: Mapped[Artwork] = relationship(back_populates="sources")


class TagType(Base):
    __tablename__ = "tag_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(100), default="")
    color: Mapped[str] = mapped_column(String(50), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    tags: Mapped[list[Tag]] = relationship(back_populates="tag_type")


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    type: Mapped[str] = mapped_column(String(50), ForeignKey("tag_types.name"), default="general")
    alias_of_id: Mapped[int | None] = mapped_column(
        ForeignKey("tags.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    alias_of: Mapped[Tag | None] = relationship(remote_side=[id])  # noqa: A003
    tag_type: Mapped[TagType | None] = relationship(back_populates="tags")
    artworks: Mapped[list[Artwork]] = relationship(secondary="artwork_tags", back_populates="tags")


class ArtworkTag(Base):
    __tablename__ = "artwork_tags"

    artwork_id: Mapped[int] = mapped_column(
        ForeignKey("artworks.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)


class BotPostLog(Base):
    __tablename__ = "bot_post_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    artwork_id: Mapped[int] = mapped_column(ForeignKey("artworks.id", ondelete="CASCADE"))
    bot_platform: Mapped[str] = mapped_column(String(50))
    channel_id: Mapped[str] = mapped_column(String(255), default="")
    message_id: Mapped[str] = mapped_column(String(255), default="")
    message_link: Mapped[str] = mapped_column(String(500), default="")
    posted_by: Mapped[str] = mapped_column(String(255), default="")
    # 关联到 users 表的发图用户（与 posted_by 字符串并存，用于统计）
    posted_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    artwork: Mapped[Artwork] = relationship(back_populates="post_logs")
    posted_by_user: Mapped[User | None] = relationship(  # noqa: F821
        foreign_keys="[BotPostLog.posted_by_user_id]"
    )


class ArtworkEmbedding(Base):
    __tablename__ = "artwork_embeddings"

    artwork_id: Mapped[int] = mapped_column(
        ForeignKey("artworks.id", ondelete="CASCADE"), primary_key=True
    )
    text_hash: Mapped[str] = mapped_column(String(64), default="")
    embedding: Mapped[bytes] = mapped_column(LargeBinary)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
