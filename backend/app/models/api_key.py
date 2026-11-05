import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.app.extensions import db


class APIKey(db.Model):
    __tablename__ = "api_keys"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(String(100), nullable=False)
    key_hash = db.Column(String(64), unique=True, nullable=False, index=True)
    last_used_at = db.Column(DateTime(timezone=True), nullable=True)
    expires_at = db.Column(DateTime(timezone=True), nullable=True)
    is_active = db.Column(Boolean, nullable=False, default=True)
    created_at = db.Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="api_keys")

    def is_valid(self) -> bool:
        if not self.is_active:
            return False
        if self.expires_at:
            now = datetime.now(timezone.utc)
            expires = self.expires_at if self.expires_at.tzinfo else self.expires_at.replace(tzinfo=timezone.utc)
            if now > expires:
                return False
        return True

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

