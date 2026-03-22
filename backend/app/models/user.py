from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True, index=True)
    tg_username: Mapped[str] = mapped_column(String(255), default="")
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    # "owner"（站长，完整权限）或 "admin"（管理员，受限权限）
    role: Mapped[str] = mapped_column(String(20), default="admin")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # 临时存储 WebAuthn challenge（每次发起认证时覆盖写入）
    webauthn_challenge: Mapped[str | None] = mapped_column(String(512), nullable=True)

    credentials: Mapped[list["WebAuthnCredential"]] = relationship(  # type: ignore[name-defined]
        back_populates="user", cascade="all, delete-orphan"
    )
