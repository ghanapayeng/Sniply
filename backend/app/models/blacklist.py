import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.app.extensions import db


class BlacklistedDomain(db.Model):
    __tablename__ = "blacklisted_domains"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain = db.Column(String(255), unique=True, nullable=False, index=True)
    reason = db.Column(String(255), nullable=True)
    is_active = db.Column(Boolean, nullable=False, default=True, index=True)
    created_by = db.Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    creator = relationship("User", foreign_keys=[created_by])

    def to_dict(self):
        return {
            "id": str(self.id),
            "domain": self.domain,
            "reason": self.reason,
            "is_active": self.is_active,
            "created_by": str(self.created_by) if self.created_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
