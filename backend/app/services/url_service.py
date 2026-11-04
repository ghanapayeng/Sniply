from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict, Any
from sqlalchemy import or_, desc, asc
from flask import current_app
from backend.app.extensions import db
from backend.app.models.url import URL
from backend.app.models.user import User
from backend.app.utils.validators import validate_url_ssrf, validate_custom_alias
from backend.app.utils.short_code import generate_short_code
from backend.app.services.blacklist_service import BlacklistService
from backend.app.services.cache_service import CacheService
from backend.app.services.security_service import SecurityService


class URLService:
    @staticmethod
    def create_url(
        original_url: str,
        user: Optional[User] = None,
        custom_alias: Optional[str] = None,
        title: Optional[str] = None,
        expires_in_days: Optional[int] = None,
        expires_at: Optional[datetime] = None,
    ) -> Tuple[Optional[URL], str]:
        """
        Create a new shortened URL with full validation:
        - SSRF protection
        - Domain blacklist check
        - Custom alias validation & uniqueness
        - Expiration calculation & policy enforcement
        - Unique short code generation
        """
        # 1. SSRF Validation
        is_valid_url, error_msg, normalized_url = validate_url_ssrf(original_url)
        if not is_valid_url:
            return None, error_msg

        # 2. Blacklist Check
        if BlacklistService.is_domain_blacklisted(normalized_url):
            return None, "The target destination domain is prohibited due to safety policies."

        # 3. Custom Alias Validation
        clean_alias = None
        if custom_alias:
            clean_alias = custom_alias.strip().lower()
            is_valid_alias, alias_err = validate_custom_alias(clean_alias)
            if not is_valid_alias:
                return None, alias_err

            # Check duplicate in DB (both short_code and custom_alias)
            existing = URL.query.filter(
                or_(URL.custom_alias == clean_alias, URL.short_code == clean_alias)
            ).first()
            if existing:
                return None, f"The alias '{clean_alias}' is already taken. Please choose another."

        # 4. Expiration Policy
        now = datetime.now(timezone.utc)
        final_expires_at = None

        if expires_at:
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at <= now:
                return None, "Expiration date must be in the future."
            final_expires_at = expires_at
        elif expires_in_days is not None and expires_in_days > 0:
            final_expires_at = now + timedelta(days=expires_in_days)

        is_anonymous = user is None
        if is_anonymous:
            # Anonymous links cannot be permanent — apply max expiry
            max_anon_days = current_app.config.get("ANONYMOUS_MAX_EXPIRY_DAYS", 30)
            max_allowed = now + timedelta(days=max_anon_days)
            if final_expires_at is None or final_expires_at > max_allowed:
                final_expires_at = max_allowed

        # 5. Generate Unique Short Code
        short_code = None
        for _ in range(5):
            candidate = generate_short_code(7)
            # Ensure not collision with existing short_code or custom_alias
            if not URL.query.filter(or_(URL.short_code == candidate, URL.custom_alias == candidate)).first():
                short_code = candidate
                break

        if not short_code:
            return None, "Failed to generate a unique short link. Please try again."

        # 6. Save URL
        new_url = URL(
            user_id=user.id if user else None,
            original_url=normalized_url,
            short_code=short_code,
            custom_alias=clean_alias,
            title=title.strip() if title else None,
            is_active=True,
            is_anonymous=is_anonymous,
            click_count=0,
            expires_at=final_expires_at,
        )
        db.session.add(new_url)
        db.session.commit()

        # Cache immediately for rapid first-click
        cls_ttl = 3600
        if final_expires_at:
            remaining = int((final_expires_at - now).total_seconds())
            cls_ttl = max(1, min(cls_ttl, remaining))

        base_url = current_app.config.get("BASE_URL", "")
        payload = new_url.to_dict(base_url=base_url)
        CacheService.set_url(short_code, payload, ttl=cls_ttl)
        if clean_alias:
            CacheService.set_url(clean_alias, payload, ttl=cls_ttl)

        if user:
            SecurityService.log_audit(
                action="url.create",
                user_id=user.id,
                resource_type="url",
                resource_id=str(new_url.id),
                details=f"Created short URL {short_code} for {normalized_url[:60]}",
            )

        return new_url, ""

    @staticmethod
    def get_url_by_code(code: str) -> Tuple[Optional[Dict[str, Any]], Optional[URL]]:
        """
        Fast lookup:
        1. Checks Redis cache.
        2. On cache miss, queries PostgreSQL by short_code (exact) OR custom_alias (lowercased).
        3. Caches result in Redis.
        Returns: (cached_dict, db_model)
        """
        clean_code = code.strip()

        # 1. Check Redis cache
        cached = CacheService.get_url(clean_code)
        if not cached and clean_code.lower() != clean_code:
            cached = CacheService.get_url(clean_code.lower())
        if cached:
            return cached, None

        # 2. Check Database
        url_obj = URL.query.filter(
            or_(URL.short_code == clean_code, URL.custom_alias == clean_code.lower())
        ).first()

        if not url_obj:
            return None, None

        # 3. Cache valid active URL
        base_url = current_app.config.get("BASE_URL", "")
        payload = url_obj.to_dict(base_url=base_url)

        if url_obj.is_accessible():
            now = datetime.now(timezone.utc)
            ttl = current_app.config.get("CACHE_DEFAULT_TIMEOUT", 3600)
            if url_obj.expires_at:
                expires = url_obj.expires_at if url_obj.expires_at.tzinfo else url_obj.expires_at.replace(tzinfo=timezone.utc)
                remaining = int((expires - now).total_seconds())
                ttl = max(1, min(ttl, remaining))
            
            CacheService.set_url(clean_code, payload, ttl=ttl)
            if url_obj.custom_alias and url_obj.custom_alias != clean_code:
                CacheService.set_url(url_obj.custom_alias, payload, ttl=ttl)

        return payload, url_obj

    @staticmethod
    def update_url(
        url_obj: URL,
        title: Optional[str] = None,
        custom_alias: Optional[str] = None,
        is_active: Optional[bool] = None,
        expires_at: Optional[datetime] = None,
    ) -> Tuple[bool, str]:
        """Update URL properties and invalidate old cache entries."""
        old_short_code = url_obj.short_code
        old_alias = url_obj.custom_alias

        if custom_alias is not None:
            clean_alias = custom_alias.strip().lower() if custom_alias else None
            if clean_alias != old_alias:
                if clean_alias:
                    is_valid, err = validate_custom_alias(clean_alias)
                    if not is_valid:
                        return False, err
                    # Check collision
                    existing = URL.query.filter(
                        or_(URL.custom_alias == clean_alias, URL.short_code == clean_alias),
                        URL.id != url_obj.id,
                    ).first()
                    if existing:
                        return False, f"Alias '{clean_alias}' is already in use."
                url_obj.custom_alias = clean_alias

        if title is not None:
            url_obj.title = title.strip() if title else None

        if is_active is not None:
            url_obj.is_active = is_active

        if expires_at is not None:
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            url_obj.expires_at = expires_at

        url_obj.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        # Invalidate cache
        CacheService.invalidate(old_short_code, old_alias)
        if url_obj.custom_alias and url_obj.custom_alias != old_alias:
            CacheService.invalidate(old_short_code, url_obj.custom_alias)

        return True, ""

    @staticmethod
    def delete_url(url_obj: URL) -> bool:
        """Delete URL and invalidate cache."""
        short_code = url_obj.short_code
        custom_alias = url_obj.custom_alias

        db.session.delete(url_obj)
        db.session.commit()

        CacheService.invalidate(short_code, custom_alias)
        return True

    @staticmethod
    def list_user_urls(
        user_id,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Dict[str, Any]:
        """Paginated list of URLs for a specific user with filtering and search."""
        query = URL.query.filter_by(user_id=user_id)

        # Search by title, original_url, short_code, custom_alias
        if search:
            pattern = f"%{search.strip().lower()}%"
            query = query.filter(
                or_(
                    URL.original_url.ilike(pattern),
                    URL.title.ilike(pattern),
                    URL.short_code.ilike(pattern),
                    URL.custom_alias.ilike(pattern),
                )
            )

        # Status filter
        now = datetime.now(timezone.utc)
        if status_filter == "active":
            query = query.filter(URL.is_active == True, or_(URL.expires_at == None, URL.expires_at > now))
        elif status_filter == "inactive":
            query = query.filter(URL.is_active == False)
        elif status_filter == "expired":
            query = query.filter(URL.expires_at != None, URL.expires_at <= now)

        # Sorting
        sort_col = getattr(URL, sort_by, URL.created_at)
        if sort_order.lower() == "asc":
            query = query.order_by(asc(sort_col))
        else:
            query = query.order_by(desc(sort_col))

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        base_url = current_app.config.get("BASE_URL", "")

        return {
            "items": [u.to_dict(base_url=base_url) for u in pagination.items],
            "total": pagination.total,
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total_pages": pagination.pages,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev,
        }
