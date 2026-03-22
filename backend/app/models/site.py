from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FriendLink(Base):
    __tablename__ = "friend_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(2048))
    description: Mapped[str] = mapped_column(String(500), default="")
    avatar_url: Mapped[str] = mapped_column(String(2048), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=100, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
