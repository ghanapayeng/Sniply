import logging
from typing import Optional, Tuple
from flask import current_app, request, has_request_context
from user_agents import parse as parse_user_agent
from backend.app.extensions import db
from backend.app.models.audit_log import AuditLog
from backend.app.utils.validators import hash_ip

logger = logging.getLogger(__name__)


class SecurityService:
    @staticmethod
    def get_client_ip(req=None) -> str:
        """Extract client IP respecting X-Forwarded-For if behind a reverse proxy like Render."""
        if req is not None:
            r = req
        elif has_request_context():
            r = request
        else:
            return "127.0.0.1"

        forwarded = r.headers.get("X-Forwarded-For")
        if forwarded:
            # First IP in comma-separated list is the client IP
            return forwarded.split(",")[0].strip()
        return r.remote_addr or "127.0.0.1"

    @classmethod
    def get_visitor_ip_hash(cls, req=None) -> str:
        """Hash visitor IP with application salt to preserve privacy."""
        ip = cls.get_client_ip(req)
        salt = current_app.config.get("IP_HASH_SALT", "sniply-salt")
        return hash_ip(ip, salt=salt)

    @staticmethod
    def parse_ua(user_agent_str: Optional[str]) -> Tuple[str, str, str]:
        """
        Parse user-agent string into: (browser, operating_system, device_type)
        device_type: desktop, mobile, tablet, bot, or other
        """
        if not user_agent_str:
            return "Unknown", "Unknown", "unknown"
        
        try:
            ua = parse_user_agent(user_agent_str)
            browser = ua.browser.family or "Unknown"
            os_name = ua.os.family or "Unknown"
            
            if ua.is_bot:
                device = "bot"
            elif ua.is_tablet:
                device = "tablet"
            elif ua.is_mobile:
                device = "mobile"
            elif ua.is_pc:
                device = "desktop"
            else:
                device = "other"

            return browser, os_name, device
        except Exception:
            return "Unknown", "Unknown", "other"

    @staticmethod
    def log_audit(
        action: str,
        user_id=None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[str] = None,
    ):
        """Record an event in the audit_logs table."""
        try:
            log_entry = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details,
            )
            db.session.add(log_entry)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error("Failed to write audit log: %s", e)
