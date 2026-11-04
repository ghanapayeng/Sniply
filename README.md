# Sniply — Enterprise Full-Stack URL Shortener

<div align="center">
  <img src="frontend/assets/logo.svg" alt="Sniply Logo" width="220" />
  <p><strong>Make Your Links Shorter. Share Them Smarter.</strong></p>
  <p>A production-ready, security-hardened, high-throughput URL shortening and link analytics platform.</p>
</div>

---

## Architecture Overview

| Component | Technology | Target Hosting |
|---|---|---|
| **Frontend** | HTML5, CSS3, Vanilla JavaScript, Fetch API, Chart.js | **Render Static Site** |
| **Backend** | Python 3.12, Flask, Flask Blueprints, REST API | **Render Web Service** |
| **Application Server**| Gunicorn WSGI (sync workers, pre-fork model) | **Render Web Service** |
| **Persistent Database**| PostgreSQL 16 (SQLAlchemy ORM + Alembic Migrations) | **Neon PostgreSQL** |
| **Cache & Limiter** | Redis (Cache-aside strategy, URL mapping, Rate limiting) | **Redis / Upstash** |
| **Containerization** | Docker, Docker Compose (multi-stage, non-root user) | **Local Dev & Deployment** |

```
                       ┌────────────────────────┐
                       │  Render Static Site    │
                       │   (HTML/CSS/JS SPA)    │
                       └───────────┬────────────┘
                                   │ HTTPS Fetch / JSON
                                   ▼
                       ┌────────────────────────┐
  Redirect Traffic ───►│   Render Web Service   │
  (GET /{short_code})  │     Flask + Gunicorn   │
                       └─────┬────────────┬─────┘
                             │            │
            Cache-Aside Check│            │ Persistent Store
                             ▼            ▼
                   ┌───────────────┐  ┌─────────────────┐
                   │ Redis Cache   │  │ Neon PostgreSQL │
                   │  (Sub-ms TTL) │  │  (SSL Pooling)  │
                   └───────────────┘  └─────────────────┘
```

---

## Key Features

1. **Anonymous & Authenticated Shortening**:
   - Visitors can immediately shorten URLs from the landing page.
   - Configurable link expiration (1 day, 7 days, 30 days, 90 days, or permanent for registered users).
   - Instant 1-click clipboard copy with visual feedback and mobile QR code generation.

2. **Custom Branded Aliases**:
   - Registered users can create memorable custom links (e.g., `https://sniply-api.onrender.com/summer-sale`).
   - Reserved-word collision protection and case-normalized duplicate detection.

3. **High-Performance Redirection**:
   - **Cache-aside Redis architecture**: Cached URLs redirect in sub-millisecond time.
   - Non-blocking, asynchronous click recording that never delays the redirect.
   - Graceful fallback: If Redis is unavailable, the application continues serving redirects from PostgreSQL without interruption.

4. **Deep Audience Analytics**:
   - Track total clicks, estimated unique visitors (privacy-preserving salted IP hashes), device breakdown (mobile, tablet, desktop), browser distribution, operating systems, and top referrers.
   - Interactive 14-day and 30-day timeline charts powered by Chart.js.
   - Detailed paginated click stream inspector.

5. **Multi-Layer Security Controls**:
   - **SSRF Defense**: Strict validation rejecting private IPs (RFC 1918), loopback, link-local, multicast, cloud metadata addresses (169.254.169.254), and non-HTTP/HTTPS schemes.
   - **Domain Blacklisting**: Exact and subdomain phishing/malware domain protection stored in PostgreSQL.
   - **Authentication**: Modern password hashing with Werkzeug (scrypt), HTTP-only SameSite cookies, Bearer token API authorization, and developer API keys.
   - **Visitor Privacy**: Raw IP addresses are **never** stored. A salted SHA-256 hash is generated and recorded.
   - **Security Headers**: HSTS, Content-Security-Policy (CSP), X-Frame-Options (DENY), nosniff, and strict referrer policy.

6. **Dedicated Administrator Suite**:
   - Real-time global telemetry: total users, global links, global clicks, and active links.
   - User account management with one-click suspension and reactivation.
   - Global link removal and prohibited domain governance.
   - Full security audit trail.

---

## Repository Directory Structure

```
sniply/
├── backend/
│   ├── app/
│   │   ├── __init__.py           # Application factory, middlewares, error handlers
│   │   ├── config.py             # Environment configurations (Dev, Testing, Prod)
│   │   ├── extensions.py         # SQLAlchemy, Migrate, Limiter, CORS, Redis
│   │   ├── models/               # All 8 PostgreSQL SQLAlchemy models
│   │   │   ├── user.py           # Users table
│   │   │   ├── url.py            # URLs table
│   │   │   ├── click_event.py    # Click events table
│   │   │   ├── blacklist.py      # Blacklisted domains table
│   │   │   ├── session.py        # User sessions table
│   │   │   ├── api_key.py        # Developer API keys table
│   │   │   ├── audit_log.py      # Security audit logs table
│   │   │   └── password_reset.py # Password reset tokens table
│   │   ├── routes/               # Flask Blueprints
│   │   │   ├── auth.py           # Register, login, logout, me, keys
│   │   │   ├── urls.py           # Shorten, list, update, delete, QR
│   │   │   ├── redirects.py      # /{short_code} high-speed redirection
│   │   │   ├── analytics.py      # Overview & detailed link analytics
│   │   │   └── admin.py          # Admin management endpoints
│   │   ├── services/             # Business logic layer
│   │   │   ├── auth_service.py
│   │   │   ├── url_service.py
│   │   │   ├── analytics_service.py
│   │   │   ├── cache_service.py
│   │   │   ├── security_service.py
│   │   │   └── blacklist_service.py
│   │   ├── middleware/           # Security headers & auth interceptors
│   │   └── utils/                # SSRF validators, base62 generator, responses
│   ├── migrations/               # Alembic database migrations
│   ├── tests/                    # Complete pytest test suite (34 tests)
│   ├── requirements.txt          # Production dependencies
│   ├── run.py                    # Local CLI & admin bootstrap entrypoint
│   ├── wsgi.py                   # Gunicorn WSGI entrypoint
│   ├── gunicorn.conf.py          # Production web server configuration
│   └── Dockerfile                # Multi-stage production container
├── frontend/
│   ├── index.html                # Landing page (screenshot-inspired UI)
│   ├── pages/
│   │   ├── login.html            # Sign in
│   │   ├── register.html         # Sign up
│   │   ├── dashboard.html        # SaaS user dashboard
│   │   ├── urls.html             # URL table management
│   │   ├── analytics.html        # Deep-dive analytics charts
│   │   ├── settings.html         # Profile, API keys, password
│   │   ├── admin.html            # Administrator suite
│   │   ├── 404.html              # Custom 404 page
│   │   ├── expired.html          # Expired link notification
│   │   └── error.html            # Disabled link notice
│   ├── css/
│   │   ├── styles.css            # Design tokens, variables, dark mode
│   │   └── dashboard.css         # SaaS dashboard layout, charts, tables
│   ├── js/
│   │   ├── config.js             # Centralized API endpoint configuration
│   │   ├── api.js                # Fetch client & toast notifications
│   │   ├── auth.js               # Session and authentication guards
│   │   ├── app.js                # Landing page controller
│   │   ├── dashboard.js          # Dashboard controller
│   │   ├── urls.js               # URL management controller
│   │   ├── analytics.js          # Analytics & Chart.js controller
│   │   ├── settings.js           # Settings controller
│   │   └── admin.js              # Admin console controller
│   └── assets/                   # SVG logo and favicon
├── database/
│   ├── schema.md                 # Complete schema reference
│   └── er-diagram.md             # Mermaid entity relationship diagram
├── render.yaml                   # Render Blueprint (Static Site + Web Service)
├── docker-compose.yml            # Local dev stack (Flask + Postgres + Redis)
├── .env.example                  # Environment configuration template
├── .gitignore                    # Secrets & artifact protection
└── LICENSE                       # MIT License
```

---

## Local Development Setup

### Option 1: Docker Compose (Fastest & Recommended)

Ensure Docker is installed, then run:

```bash
docker compose up --build -d
```

Verify all services are healthy:

```bash
docker compose ps
docker compose logs -f backend
```

The application will be live at `http://localhost:5000`.

---

### Option 2: Local Python Virtual Environment

1. **Clone the repository:**
   ```bash
   git clone <repo-url> sniply
   cd sniply
   ```

2. **Create and activate a Python 3.12+ virtual environment:**
   ```bash
   python3 -m venv backend/.venv
   source backend/.venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r backend/requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your local PostgreSQL and Redis credentials
   ```

5. **Run database migrations:**
   ```bash
   PYTHONPATH=. flask --app backend.run:app db upgrade -d backend/migrations
   ```

6. **Bootstrap the Administrator Account:**
   ```bash
   ADMIN_BOOTSTRAP_PASSWORD="YourSecurePassword!" PYTHONPATH=. python backend/run.py bootstrap-admin
   ```

7. **Start the local server:**
   ```bash
   PYTHONPATH=. python backend/run.py
   ```
   Open `http://localhost:5000` in your browser.

---

## Running Automated Tests

Sniply includes an exhaustive automated test suite with an isolated test database and Redis cache testing:

```bash
PYTHONPATH=. backend/.venv/bin/pytest backend/tests -v --cov=backend/app
```

**Test Modules:**
- `test_auth.py`: Registration, login, passwords, session revocation, API keys.
- `test_urls.py`: Anonymous shortening, custom aliases, duplicates, pagination, QR codes.
- `test_redirects.py`: 302 redirects, disabled link blocking, expired link handling.
- `test_security.py`: SSRF private IP blocking, domain blacklists, security headers.
- `test_analytics.py`: Real click tracking, visitor privacy, user isolation.
- `test_cache.py`: Cache hits, invalidation on update/delete, graceful Redis fallback.

---

## Neon PostgreSQL Setup

Sniply uses Neon PostgreSQL for production persistence.

1. Create a project at [Neon](https://neon.tech).
2. Create a database named `sniply`.
3. Copy your connection string from the Neon dashboard. It looks like:
   ```
   postgresql://username:password@ep-cool-fog-123456.us-east-2.aws.neon.tech/sniply?sslmode=require
   ```
4. Set this as `DATABASE_URL` in your Render Environment Variables.
5. In production, Neon connection strings use connection pooling and SSL encryption automatically.

---

## Render Deployment Guide

### Deploying via Render Blueprint (`render.yaml`)

1. Push your repository to **GitHub**.
2. Log in to [Render](https://dashboard.render.com).
3. Click **New +** → **Blueprint**.
4. Select your `sniply` repository. Render automatically reads `render.yaml` and provisions:
   - `sniply-web`: Render Static Site serving `./frontend`.
   - `sniply-api`: Render Web Service running Flask + Gunicorn.
5. Fill in the required environment variables prompted by Render:
   - `DATABASE_URL`: Your Neon PostgreSQL connection string.
   - `REDIS_URL`: Your Redis service connection string (e.g., Upstash Redis).
   - `ADMIN_BOOTSTRAP_PASSWORD`: Strong password for the initial admin account.

---

## REST API Reference

All API routes are prefixed with `/api/v1`.

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | Register new user | No |
| `POST` | `/api/v1/auth/login` | Log in and receive session/token | No |
| `POST` | `/api/v1/auth/logout` | Revoke session | Yes |
| `GET` | `/api/v1/auth/me` | Current authenticated user details | Yes |
| `POST` | `/api/v1/auth/change-password` | Update account password | Yes |
| `POST` | `/api/v1/auth/api-keys` | Generate new developer API key | Yes |
| `GET` | `/api/v1/auth/api-keys` | List developer API keys | Yes |
| `DELETE` | `/api/v1/auth/api-keys/{id}` | Revoke developer API key | Yes |
| `POST` | `/api/v1/urls` | Shorten URL (anonymous or authenticated) | No |
| `GET` | `/api/v1/urls` | Paginated list of user URLs | Yes |
| `GET` | `/api/v1/urls/{short_code}` | Get URL details | Yes |
| `PATCH` | `/api/v1/urls/{short_code}` | Update title, alias, or active status | Yes |
| `DELETE` | `/api/v1/urls/{short_code}` | Delete URL | Yes |
| `GET` | `/api/v1/urls/{short_code}/qr` | Generate QR code PNG | No |
| `GET` | `/api/v1/analytics/overview` | User dashboard high-level metrics | Yes |
| `GET` | `/api/v1/analytics/{short_code}` | Detailed breakdown for a single URL | Yes |
| `GET` | `/api/v1/analytics/{short_code}/clicks` | Paginated click event stream | Yes |
| `GET` | `/api/v1/admin/overview` | System-wide statistics | Admin |
| `GET` | `/api/v1/admin/users` | List all platform users | Admin |
| `PATCH` | `/api/v1/admin/users/{id}/status`| Suspend or activate user | Admin |
| `GET` | `/api/v1/admin/urls` | Global URL list | Admin |
| `DELETE` | `/api/v1/admin/urls/{short_code}`| Admin delete URL | Admin |
| `GET` | `/api/v1/admin/domains` | List prohibited domains | Admin |
| `POST` | `/api/v1/admin/domains` | Add domain to blacklist | Admin |
| `DELETE` | `/api/v1/admin/domains/{domain}` | Remove domain from blacklist | Admin |
| `GET` | `/api/v1/admin/audit-logs` | Security audit trail | Admin |
| `GET` | `/{short_code}` | High-speed link redirection | No |
| `GET` | `/health` | Application healthcheck | No |

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
