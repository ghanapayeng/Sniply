import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Boolean, Integer, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.app.extensions import db


class URL(db.Model):
    __tablename__ = "urls"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    original_url = db.Column(Text, nullable=False)
    short_code = db.Column(String(32), unique=True, nullable=False, index=True)
    custom_alias = db.Column(String(64), unique=True, nullable=True, index=True)
    title = db.Column(String(255), nullable=True)
    is_active = db.Column(Boolean, nullable=False, default=True, index=True)
    is_anonymous = db.Column(Boolean, nullable=False, default=False, index=True)
    click_count = db.Column(Integer, nullable=False, default=0)
    expires_at = db.Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = db.Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = db.Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = relationship("User", back_populates="urls")
    click_events = relationship("ClickEvent", back_populates="url", cascade="all, delete-orphan", lazy="select")

    __table_args__ = (
        Index("idx_urls_active_expires", "is_active", "expires_at"),
        Index("idx_urls_user_created", "user_id", "created_at"),
    )

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        now = datetime.now(timezone.utc)
        expires = self.expires_at if self.expires_at.tzinfo else self.expires_at.replace(tzinfo=timezone.utc)
        return now > expires

    def is_accessible(self) -> bool:
        return self.is_active and not self.is_expired()

    def to_dict(self, base_url: str = ""):
        effective_code = self.custom_alias or self.short_code
        short_url = f"{base_url.rstrip('/')}/{effective_code}" if base_url else f"/{effective_code}"
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "original_url": self.original_url,
            "short_code": self.short_code,
            "custom_alias": self.custom_alias,
            "title": self.title,
            "is_active": self.is_active,
            "is_anonymous": self.is_anonymous,
            "click_count": self.click_count,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_expired": self.is_expired(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "short_url": short_url,
        }
