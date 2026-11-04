from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from flask import current_app, request, has_request_context
from werkzeug.security import generate_password_hash, check_password_hash
from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.models.session import UserSession
from backend.app.models.api_key import APIKey
from backend.app.utils.short_code import generate_session_token
from backend.app.utils.validators import hash_token
from backend.app.services.security_service import SecurityService


class AuthService:
    @staticmethod
    def register_user(username: str, email: str, password: str, role: str = "user") -> Tuple[Optional[User], str]:
        """Register a new user account with secure password hashing."""
        clean_user = username.strip().lower()
        clean_email = email.strip().lower()

        if User.query.filter_by(username=clean_user).first():
            return None, "A user with this username already exists."

        if User.query.filter_by(email=clean_email).first():
            return None, "A user with this email address already exists."

        # Werkzeug generates modern secure hashes (scrypt or pbkdf2)
        password_hash = generate_password_hash(password)

        new_user = User(
            username=clean_user,
            email=clean_email,
            password_hash=password_hash,
            role=role,
            is_active=True,
            email_verified=False,
        )
        db.session.add(new_user)
        db.session.commit()

        SecurityService.log_audit(
            action="auth.register",
            user_id=new_user.id,
            resource_type="user",
            resource_id=str(new_user.id),
            details=f"Registered user: {clean_user}",
        )
        return new_user, ""

    @staticmethod
    def authenticate_user(identifier: str, password: str) -> Tuple[Optional[User], str]:
        """Verify user credentials by username or email."""
        clean_id = identifier.strip().lower()
        user = User.query.filter(
            (User.username == clean_id) | (User.email == clean_id)
        ).first()

        if not user:
            return None, "Invalid email/username or password."

        if not user.is_active:
            return None, "Account has been suspended. Please contact support."

        if not check_password_hash(user.password_hash, password):
            return None, "Invalid email/username or password."

        # Update last login timestamp
        user.last_login_at = datetime.now(timezone.utc)
        db.session.commit()

        SecurityService.log_audit(
            action="auth.login",
            user_id=user.id,
            resource_type="user",
            resource_id=str(user.id),
            details=f"User logged in from IP: {SecurityService.get_visitor_ip_hash()[:8]}...",
        )
        return user, ""

    @staticmethod
    def create_session(user: User, req=None) -> Tuple[str, UserSession]:
        """Create a new session, store its hash in PostgreSQL, and return raw secret token."""
        raw_token = generate_session_token()
        token_hash = hash_token(raw_token)

        lifetime = current_app.config.get("SESSION_LIFETIME", timedelta(days=14))
        expires_at = datetime.now(timezone.utc) + lifetime

        ip_hash = SecurityService.get_visitor_ip_hash(req)
        if req:
            user_agent = req.headers.get("User-Agent")
        elif has_request_context():
            user_agent = request.headers.get("User-Agent")
        else:
            user_agent = None

        session = UserSession(
            user_id=user.id,
            session_identifier_hash=token_hash,
            ip_hash=ip_hash,
            user_agent=user_agent[:512] if user_agent else None,
            expires_at=expires_at,
        )
        db.session.add(session)
        db.session.commit()
        return raw_token, session

    @staticmethod
    def revoke_session(raw_token: str) -> bool:
        """Revoke a session by token hash."""
        if not raw_token:
            return False
        token_hash = hash_token(raw_token)
        session = UserSession.query.filter_by(session_identifier_hash=token_hash).first()
        if session and session.revoked_at is None:
            session.revoked_at = datetime.now(timezone.utc)
            db.session.commit()
            return True
        return False

    @staticmethod
    def get_user_from_token(raw_token: str) -> Optional[User]:
        """Validate session token and return the associated active user."""
        if not raw_token:
            return None
        token_hash = hash_token(raw_token)
        session = UserSession.query.filter_by(session_identifier_hash=token_hash).first()

        if not session or not session.is_valid():
            return None

        # Update last activity
        session.last_activity_at = datetime.now(timezone.utc)
        db.session.commit()

        if not session.user or not session.user.is_active:
            return None

        return session.user

    @staticmethod
    def get_user_from_api_key(raw_key: str) -> Optional[User]:
        """Authenticate via API key."""
        if not raw_key:
            return None
        key_hash = hash_token(raw_key)
        api_key = APIKey.query.filter_by(key_hash=key_hash).first()
        if not api_key or not api_key.is_valid():
            return None

        api_key.last_used_at = datetime.now(timezone.utc)
        db.session.commit()

        if not api_key.user or not api_key.user.is_active:
            return None
        return api_key.user

    @staticmethod
    def change_password(user: User, old_password: str, new_password: str) -> Tuple[bool, str]:
        """Safely change user password and revoke other active sessions."""
        if not check_password_hash(user.password_hash, old_password):
            return False, "Current password is incorrect."

        user.password_hash = generate_password_hash(new_password)
        user.updated_at = datetime.now(timezone.utc)

        # Invalidate all prior sessions for session fixation & theft protection
        UserSession.query.filter_by(user_id=user.id, revoked_at=None).update(
            {"revoked_at": datetime.now(timezone.utc)}
        )
        db.session.commit()

        SecurityService.log_audit(
            action="auth.change_password",
            user_id=user.id,
            resource_type="user",
            resource_id=str(user.id),
            details="Password changed and prior sessions revoked",
        )
        return True, ""

    @staticmethod
    def delete_account(user: User, password: str) -> Tuple[bool, str]:
        """Permanently delete user account and associated resources."""
        if not check_password_hash(user.password_hash, password):
            return False, "Password confirmation is incorrect."

        user_id = user.id
        db.session.delete(user)
        db.session.commit()

        SecurityService.log_audit(
            action="auth.delete_account",
            user_id=None,
            resource_type="user",
            resource_id=str(user_id),
            details="Account permanently deleted",
        )
        return True, ""
