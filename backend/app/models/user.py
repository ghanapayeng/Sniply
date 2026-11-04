import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = db.Column(String(64), unique=True, nullable=False, index=True)
    email = db.Column(String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(String(255), nullable=False)
    role = db.Column(String(20), nullable=False, default="user")  # 'user' | 'admin'
    is_active = db.Column(Boolean, nullable=False, default=True)
    email_verified = db.Column(Boolean, nullable=False, default=False)
    created_at = db.Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    last_login_at = db.Column(DateTime(timezone=True), nullable=True)

    # Relationships
    urls = relationship("URL", back_populates="user", cascade="all, delete-orphan", lazy="select")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan", lazy="select")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan", lazy="select")
    audit_logs = relationship("AuditLog", back_populates="user", lazy="select")
    password_resets = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan", lazy="select")

    def to_dict(self, include_admin_fields=False):
        data = {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "email_verified": self.email_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }
        if include_admin_fields:
            data["updated_at"] = self.updated_at.isoformat() if self.updated_at else None
        return data

    def is_admin(self) -> bool:
        return self.role == "admin"
