from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class WebAuthnCredential(Base):
    __tablename__ = "webauthn_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # base64url 编码的 credential ID（浏览器端唯一标识）
    credential_id: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    # CBOR 编码的公钥，以 base64url 字符串存储
    public_key: Mapped[str] = mapped_column(Text)
    # 单调递增计数器，用于防止凭据克隆攻击
    sign_count: Mapped[int] = mapped_column(Integer, default=0)
    # 用户自定义设备名称，例如 "iPhone Face ID"
    device_name: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship(back_populates="credentials")  # type: ignore[name-defined]
