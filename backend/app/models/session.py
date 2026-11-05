import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.app.extensions import db


class UserSession(db.Model):
    __tablename__ = "user_sessions"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_identifier_hash = db.Column(String(64), unique=True, nullable=False, index=True)
    ip_hash = db.Column(String(64), nullable=True)
    user_agent = db.Column(String(512), nullable=True)
    created_at = db.Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    last_activity_at = db.Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    expires_at = db.Column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at = db.Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="sessions")

    __table_args__ = (
        Index("idx_sessions_user_active", "user_id", "expires_at", "revoked_at"),
    )

    def is_valid(self) -> bool:
        if self.revoked_at is not None:
            return False
        now = datetime.now(timezone.utc)
        expires = self.expires_at if self.expires_at.tzinfo else self.expires_at.replace(tzinfo=timezone.utc)
        return now < expires

