import urllib.parse
from typing import Optional, List
from backend.app.extensions import db
from backend.app.models.blacklist import BlacklistedDomain


class BlacklistService:
    @staticmethod
    def extract_domain(raw_url_or_domain: str) -> str:
        """Extract clean lowercased domain from a URL or raw domain string."""
        raw = raw_url_or_domain.strip().lower()
        if "://" in raw:
            try:
                parsed = urllib.parse.urlsplit(raw)
                host = parsed.hostname or raw
            except Exception:
                host = raw
        else:
            host = raw.split("/")[0].split(":")[0]
        return host.strip().lower()

    @classmethod
    def is_domain_blacklisted(cls, url: str) -> bool:
        """
        Check if target URL domain or any of its parent domains are active in blacklisted_domains.
        Matches exact domain and subdomains (e.g., bad.com blocks evil.bad.com).
        """
        domain = cls.extract_domain(url)
        if not domain:
            return False

        # Query all active blacklisted domains
        # (For typical deployment sizes, active blacklisted domains are in the dozens to hundreds)
        blacklisted = BlacklistedDomain.query.filter_by(is_active=True).all()
        for b in blacklisted:
            b_domain = b.domain.lower()
            if domain == b_domain or domain.endswith(f".{b_domain}"):
                return True
        return False

    @classmethod
    def add_domain(cls, domain: str, reason: Optional[str] = None, user_id=None) -> BlacklistedDomain:
        clean_domain = cls.extract_domain(domain)
        existing = BlacklistedDomain.query.filter_by(domain=clean_domain).first()
        if existing:
            existing.is_active = True
            if reason:
                existing.reason = reason
            db.session.commit()
            return existing

        new_entry = BlacklistedDomain(
            domain=clean_domain,
            reason=reason,
            is_active=True,
            created_by=user_id,
        )
        db.session.add(new_entry)
        db.session.commit()
        return new_entry

    @classmethod
    def remove_domain(cls, domain: str) -> bool:
        clean_domain = cls.extract_domain(domain)
        entry = BlacklistedDomain.query.filter_by(domain=clean_domain).first()
        if entry:
            db.session.delete(entry)
            db.session.commit()
            return True
        return False

    @classmethod
    def list_domains(cls) -> List[BlacklistedDomain]:
        return BlacklistedDomain.query.order_by(BlacklistedDomain.created_at.desc()).all()
