from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Author(Base):
    __tablename__ = "authors"
    __table_args__ = (UniqueConstraint("platform", "platform_uid", name="uq_authors_platform_uid"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    platform: Mapped[str] = mapped_column(String(50), index=True)
    platform_uid: Mapped[str] = mapped_column(String(255), default="")
    # 自引用：指向同一作者的规范实体（用于跨平台合并）
    canonical_id: Mapped[int | None] = mapped_column(
        ForeignKey("authors.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    canonical: Mapped[Author | None] = relationship(remote_side=[id])
    artworks: Mapped[list[Artwork]] = relationship(back_populates="author_ref")  # type: ignore[name-defined]
