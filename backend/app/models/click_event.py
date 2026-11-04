from datetime import datetime, timezone
from sqlalchemy import BigInteger, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.app.extensions import db


class ClickEvent(db.Model):
    __tablename__ = "click_events"

    id = db.Column(BigInteger, primary_key=True, autoincrement=True)
    url_id = db.Column(UUID(as_uuid=True), ForeignKey("urls.id", ondelete="CASCADE"), nullable=False, index=True)
    clicked_at = db.Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    referrer = db.Column(String(512), nullable=True)
    user_agent = db.Column(String(512), nullable=True)
    browser = db.Column(String(64), nullable=True, index=True)
    operating_system = db.Column(String(64), nullable=True, index=True)
    device_type = db.Column(String(32), nullable=True, index=True)  # mobile, desktop, tablet, bot, unknown
    visitor_ip_hash = db.Column(String(64), nullable=False, index=True)
    country = db.Column(String(64), nullable=True)
    region = db.Column(String(64), nullable=True)

    # Relationships
    url = relationship("URL", back_populates="click_events")

    __table_args__ = (
        Index("idx_clicks_url_time", "url_id", "clicked_at"),
        Index("idx_clicks_url_visitor", "url_id", "visitor_ip_hash"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "url_id": str(self.url_id),
            "clicked_at": self.clicked_at.isoformat() if self.clicked_at else None,
            "referrer": self.referrer,
            "browser": self.browser,
            "operating_system": self.operating_system,
            "device_type": self.device_type,
            "country": self.country,
            "region": self.region,
        }
