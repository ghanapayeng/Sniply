from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from sqlalchemy import func, desc
from backend.app.extensions import db
from backend.app.models.url import URL
from backend.app.models.click_event import ClickEvent
from backend.app.services.security_service import SecurityService


class AnalyticsService:
    @staticmethod
    def record_click(url_id, req=None):
        """Record click event asynchronously / non-blocking without delaying redirect."""
        try:
            ip_hash = SecurityService.get_visitor_ip_hash(req)
            user_agent = req.headers.get("User-Agent", "") if req else ""
            referrer = req.headers.get("Referer", "") if req else ""

            browser, os_name, device = SecurityService.parse_ua(user_agent)

            # Insert click event
            event = ClickEvent(
                url_id=url_id,
                clicked_at=datetime.now(timezone.utc),
                referrer=referrer[:512] if referrer else "Direct",
                user_agent=user_agent[:512] if user_agent else None,
                browser=browser,
                operating_system=os_name,
                device_type=device,
                visitor_ip_hash=ip_hash,
            )
            db.session.add(event)

            # Atomic increment on URL table
            URL.query.filter_by(id=url_id).update({URL.click_count: URL.click_count + 1})
            db.session.commit()
        except Exception:
            db.session.rollback()

    @staticmethod
    def get_overview_analytics(user_id) -> Dict[str, Any]:
        """Aggregate high-level metrics for user dashboard."""
        now = datetime.now(timezone.utc)

        # Total links
        total_links = URL.query.filter_by(user_id=user_id).count()

        # Total clicks
        total_clicks = (
            db.session.query(func.coalesce(func.sum(URL.click_count), 0))
            .filter(URL.user_id == user_id)
            .scalar()
        )

        # Active links
        active_links = URL.query.filter(
            URL.user_id == user_id,
            URL.is_active == True,
            db.or_(URL.expires_at == None, URL.expires_at > now),
        ).count()

        # Expired links
        expired_links = URL.query.filter(
            URL.user_id == user_id,
            URL.expires_at != None,
            URL.expires_at <= now,
        ).count()

        # Top 5 links by clicks
        top_links = (
            URL.query.filter_by(user_id=user_id)
            .order_by(desc(URL.click_count))
            .limit(5)
            .all()
        )

        # Recent 5 links
        recent_links = (
            URL.query.filter_by(user_id=user_id)
            .order_by(desc(URL.created_at))
            .limit(5)
            .all()
        )

        # Daily clicks for the last 14 days
        fourteen_days_ago = now - timedelta(days=14)
        daily_query = (
            db.session.query(
                func.date_trunc("day", ClickEvent.clicked_at).label("day"),
                func.count(ClickEvent.id).label("count"),
            )
            .join(URL, ClickEvent.url_id == URL.id)
            .filter(URL.user_id == user_id, ClickEvent.clicked_at >= fourteen_days_ago)
            .group_by("day")
            .order_by("day")
            .all()
        )

        # Fill in missing dates with 0 so chart is smooth and accurate
        daily_map = {row.day.strftime("%Y-%m-%d"): row.count for row in daily_query if row.day}
        daily_clicks = []
        for i in range(14, -1, -1):
            day_str = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            daily_clicks.append({"date": day_str, "clicks": daily_map.get(day_str, 0)})

        return {
            "total_links": total_links,
            "total_clicks": total_clicks,
            "active_links": active_links,
            "expired_links": expired_links,
            "top_links": [u.to_dict() for u in top_links],
            "recent_links": [u.to_dict() for u in recent_links],
            "daily_clicks": daily_clicks,
        }

    @staticmethod
    def get_url_analytics(url_id, days: int = 30) -> Dict[str, Any]:
        """Aggregate detailed metrics for a specific URL."""
        url_obj = URL.query.filter_by(id=url_id).first()
        if not url_obj:
            return {}

        now = datetime.now(timezone.utc)
        since = now - timedelta(days=days)

        # Total clicks & Unique visitors
        total_clicks = ClickEvent.query.filter_by(url_id=url_id).count()
        unique_visitors = (
            db.session.query(func.count(func.distinct(ClickEvent.visitor_ip_hash)))
            .filter(ClickEvent.url_id == url_id)
            .scalar()
            or 0
        )

        # Breakdown by browser
        browsers = (
            db.session.query(
                func.coalesce(ClickEvent.browser, "Unknown").label("name"),
                func.count(ClickEvent.id).label("count"),
            )
            .filter(ClickEvent.url_id == url_id)
            .group_by("name")
            .order_by(desc("count"))
            .limit(10)
            .all()
        )

        # Breakdown by OS
        os_breakdown = (
            db.session.query(
                func.coalesce(ClickEvent.operating_system, "Unknown").label("name"),
                func.count(ClickEvent.id).label("count"),
            )
            .filter(ClickEvent.url_id == url_id)
            .group_by("name")
            .order_by(desc("count"))
            .limit(10)
            .all()
        )

        # Breakdown by device type
        devices = (
            db.session.query(
                func.coalesce(ClickEvent.device_type, "other").label("name"),
                func.count(ClickEvent.id).label("count"),
            )
            .filter(ClickEvent.url_id == url_id)
            .group_by("name")
            .order_by(desc("count"))
            .all()
        )

        # Top referrers
        referrers = (
            db.session.query(
                func.coalesce(ClickEvent.referrer, "Direct").label("name"),
                func.count(ClickEvent.id).label("count"),
            )
            .filter(ClickEvent.url_id == url_id)
            .group_by("name")
            .order_by(desc("count"))
            .limit(10)
            .all()
        )

        # Timeline for past N days
        timeline_query = (
            db.session.query(
                func.date_trunc("day", ClickEvent.clicked_at).label("day"),
                func.count(ClickEvent.id).label("count"),
            )
            .filter(ClickEvent.url_id == url_id, ClickEvent.clicked_at >= since)
            .group_by("day")
            .order_by("day")
            .all()
        )
        timeline_map = {row.day.strftime("%Y-%m-%d"): row.count for row in timeline_query if row.day}
        timeline = []
        for i in range(days, -1, -1):
            d_str = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            timeline.append({"date": d_str, "clicks": timeline_map.get(d_str, 0)})

        return {
            "url": url_obj.to_dict(),
            "total_clicks": total_clicks,
            "unique_visitors": unique_visitors,
            "browsers": [{"name": b.name, "count": b.count} for b in browsers],
            "operating_systems": [{"name": o.name, "count": o.count} for o in os_breakdown],
            "devices": [{"name": d.name, "count": d.count} for d in devices],
            "referrers": [{"name": r.name, "count": r.count} for r in referrers],
            "timeline": timeline,
        }

    @staticmethod
    def get_url_clicks_paginated(url_id, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Paginated list of individual click events for a URL."""
        pagination = (
            ClickEvent.query.filter_by(url_id=url_id)
            .order_by(desc(ClickEvent.clicked_at))
            .paginate(page=page, per_page=per_page, error_out=False)
        )
        return {
            "items": [c.to_dict() for c in pagination.items],
            "total": pagination.total,
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total_pages": pagination.pages,
        }

