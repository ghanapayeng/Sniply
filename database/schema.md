# Sniply PostgreSQL Database Schema Documentation

This document describes the production database schema for **Sniply**, hosted on Neon PostgreSQL.

---

## 1. Table: `users`
Represents registered users and platform administrators.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | PRIMARY KEY, DEFAULT `uuid_generate_v4()` | Unique user identifier |
| `username` | `VARCHAR(64)` | UNIQUE, NOT NULL, INDEXED | Normalized username (lowercase, 3-30 chars) |
| `email` | `VARCHAR(255)` | UNIQUE, NOT NULL, INDEXED | Contact & authentication email |
| `password_hash` | `VARCHAR(255)` | NOT NULL | Werkzeug scrypt/pbkdf2 salted hash |
| `role` | `VARCHAR(20)` | NOT NULL, DEFAULT `'user'` | Role `'user'` or `'admin'` |
| `is_active` | `BOOLEAN` | NOT NULL, DEFAULT `TRUE` | Account active state (false = suspended) |
| `email_verified`| `BOOLEAN` | NOT NULL, DEFAULT `FALSE` | Email verification flag |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT `NOW()` | Registration timestamp |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT `NOW()` | Last profile update timestamp |
| `last_login_at` | `TIMESTAMPTZ` | NULLABLE | Most recent successful authentication |

---

## 2. Table: `urls`
Stores all shortened links (both anonymous and authenticated).

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | PRIMARY KEY, DEFAULT `uuid_generate_v4()` | Unique link record ID |
| `user_id` | `UUID` | NULLABLE, FK -> `users.id` (ON DELETE SET NULL), INDEXED | Owning user ID (NULL if anonymous) |
| `original_url` | `TEXT` | NOT NULL | Validated destination URL (HTTP/HTTPS) |
| `short_code` | `VARCHAR(32)` | UNIQUE, NOT NULL, INDEXED | Cryptographically random Base62 code |
| `custom_alias` | `VARCHAR(64)` | UNIQUE, NULLABLE, INDEXED | Optional human-readable alias |
| `title` | `VARCHAR(255)` | NULLABLE | Custom user label |
| `is_active` | `BOOLEAN` | NOT NULL, DEFAULT `TRUE`, INDEXED | Active toggle |
| `is_anonymous` | `BOOLEAN` | NOT NULL, DEFAULT `FALSE`, INDEXED | Anonymous creation flag |
| `click_count` | `INTEGER` | NOT NULL, DEFAULT `0` | Atomic click counter |
| `expires_at` | `TIMESTAMPTZ` | NULLABLE, INDEXED | Link expiration timestamp |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT `NOW()`, INDEXED | Link creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT `NOW()` | Last modification timestamp |

**Composite Indexes:**
- `idx_urls_active_expires` ON (`is_active`, `expires_at`)
- `idx_urls_user_created` ON (`user_id`, `created_at`)

---

## 3. Table: `click_events`
Records raw click events for analytics and visitor channel insights.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `BIGINT` | PRIMARY KEY, GENERATED ALWAYS AS IDENTITY | Monotonic click ID |
| `url_id` | `UUID` | NOT NULL, FK -> `urls.id` (ON DELETE CASCADE), INDEXED | Parent URL |
| `clicked_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT `NOW()`, INDEXED | Event timestamp |
| `referrer` | `VARCHAR(512)` | NULLABLE | HTTP Referer string (or 'Direct') |
| `user_agent` | `VARCHAR(512)` | NULLABLE | Client User-Agent string |
| `browser` | `VARCHAR(64)` | NULLABLE, INDEXED | Extracted browser family |
| `operating_system`| `VARCHAR(64)` | NULLABLE, INDEXED | Extracted OS family |
| `device_type` | `VARCHAR(32)` | NULLABLE, INDEXED | 'desktop', 'mobile', 'tablet', etc. |
| `visitor_ip_hash`| `VARCHAR(64)` | NOT NULL, INDEXED | Salted SHA-256 hash (never raw IP) |
| `country` | `VARCHAR(64)` | NULLABLE | Geolocation country name |
| `region` | `VARCHAR(64)` | NULLABLE | Geolocation region |

**Composite Indexes:**
- `idx_clicks_url_time` ON (`url_id`, `clicked_at`)
- `idx_clicks_url_visitor` ON (`url_id`, `visitor_ip_hash`)

---

## 4. Table: `blacklisted_domains`
Stores prohibited domains that are blocked platform-wide.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | PRIMARY KEY, DEFAULT `uuid_generate_v4()` | Prohibited domain record ID |
| `domain` | `VARCHAR(255)` | UNIQUE, NOT NULL, INDEXED | Normalized domain name (lowercase) |
| `reason` | `VARCHAR(255)` | NULLABLE | Administrative justification |
| `is_active` | `BOOLEAN` | NOT NULL, DEFAULT `TRUE`, INDEXED | Active filtering state |
| `created_by` | `UUID` | NULLABLE, FK -> `users.id` (ON DELETE SET NULL) | Admin who logged the block |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT `NOW()` | Record created timestamp |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT `NOW()` | Record updated timestamp |

---

## 5. Table: `user_sessions`
Manages authenticated web browser sessions.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | PRIMARY KEY, DEFAULT `uuid_generate_v4()` | Session record ID |
| `user_id` | `UUID` | NOT NULL, FK -> `users.id` (ON DELETE CASCADE), INDEXED | Associated user ID |
| `session_identifier_hash` | `VARCHAR(64)` | UNIQUE, NOT NULL, INDEXED | SHA-256 hash of session secret |
| `ip_hash` | `VARCHAR(64)` | NULLABLE | Salted hash of client IP |
| `user_agent` | `VARCHAR(512)` | NULLABLE | Client User-Agent |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT `NOW()` | Login timestamp |
| `last_activity_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT `NOW()` | Sliding activity timestamp |
| `expires_at` | `TIMESTAMPTZ` | NOT NULL, INDEXED | Hard expiration timestamp |
| `revoked_at` | `TIMESTAMPTZ` | NULLABLE | Revocation timestamp (logout/password change) |

**Composite Indexes:**
- `idx_sessions_user_active` ON (`user_id`, `expires_at`, `revoked_at`)

---

## 6. Table: `api_keys`
Stores hashed developer API keys for programmatic access.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | PRIMARY KEY, DEFAULT `uuid_generate_v4()` | Key ID |
| `user_id` | `UUID` | NOT NULL, FK -> `users.id` (ON DELETE CASCADE), INDEXED | Owning user |
| `name` | `VARCHAR(100)` | NOT NULL | Human-readable key label |
| `key_hash` | `VARCHAR(64)` | UNIQUE, NOT NULL, INDEXED | SHA-256 hash of API secret |
| `last_used_at` | `TIMESTAMPTZ` | NULLABLE | Last API call timestamp |
| `expires_at` | `TIMESTAMPTZ` | NULLABLE | Optional key expiry date |
| `is_active` | `BOOLEAN` | NOT NULL, DEFAULT `TRUE` | Key active state |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT `NOW()` | Creation timestamp |

---

## 7. Table: `audit_logs`
Immutable security and administrative audit trail.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | PRIMARY KEY, DEFAULT `uuid_generate_v4()` | Audit record ID |
| `user_id` | `UUID` | NULLABLE, FK -> `users.id` (ON DELETE SET NULL), INDEXED | Actor user ID |
| `action` | `VARCHAR(64)` | NOT NULL, INDEXED | Action identifier |
| `resource_type` | `VARCHAR(64)` | NULLABLE | e.g., 'user', 'url', 'domain' |
| `resource_id` | `VARCHAR(64)` | NULLABLE | Target entity ID |
| `details` | `TEXT` | NULLABLE | Contextual description or JSON |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT `NOW()`, INDEXED | Log timestamp |

**Composite Indexes:**
- `idx_audit_action_time` ON (`action`, `created_at`)

---

## 8. Table: `password_reset_tokens`
Stores one-time password recovery tokens.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | PRIMARY KEY, DEFAULT `uuid_generate_v4()` | Token record ID |
| `user_id` | `UUID` | NOT NULL, FK -> `users.id` (ON DELETE CASCADE), INDEXED | Target user |
| `token_hash` | `VARCHAR(64)` | UNIQUE, NOT NULL, INDEXED | SHA-256 hash of reset secret |
| `expires_at` | `TIMESTAMPTZ` | NOT NULL, INDEXED | Token expiration |
| `used_at` | `TIMESTAMPTZ` | NULLABLE | Timestamp token was consumed |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT `NOW()` | Token generation timestamp |

