# NQTaxi Backend

Django REST API for the NQTaxi rider application.

## Tech stack

| Layer | Technology |
|-------|------------|
| Framework | Django 4.2+ / 6.x |
| API | Django REST Framework |
| Auth | JWT (djangorestframework-simplejwt) |
| Database | PostgreSQL |
| Payments | Razorpay |
| API docs | drf-spectacular (OpenAPI 3 / Swagger) |
| Config | python-decouple (`.env`) |

## First-time setup

```powershell
# Windows
.\scripts\setup.ps1
```

```bash
# macOS / Linux
chmod +x scripts/setup.sh && ./scripts/setup.sh
```

Or manually:

```bash
python -m venv ../.venv
source ../.venv/bin/activate          # Windows: ..\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env                  # Windows: copy .env.example .env
docker compose up -d                  # optional local Postgres
python manage.py migrate
python manage.py runserver
```

## Environment variables

Copy `.env.example` to `.env` and configure:

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | Django secret key (unique per environment) |
| `DEBUG` | Yes | `True` for local dev, `False` in production |
| `ALLOWED_HOSTS` | Yes | Comma-separated hostnames |
| `DB_NAME` | Yes | PostgreSQL database name |
| `DB_USER` | Yes | PostgreSQL user |
| `DB_PASSWORD` | Yes | PostgreSQL password |
| `DB_HOST` | Yes | DB host (`localhost` with Docker) |
| `DB_PORT` | Yes | DB port (default `5432`) |
| `ACCESS_TOKEN_LIFETIME_MINUTES` | No | JWT access token TTL (default `60`) |
| `REFRESH_TOKEN_LIFETIME_DAYS` | No | JWT refresh token TTL (default `7`) |
| `RAZORPAY_KEY_ID` | Wallet APIs | Razorpay test/live key ID |
| `RAZORPAY_KEY_SECRET` | Wallet APIs | Razorpay secret |
| `RAZORPAY_AUTO_COMPLETE_TOPUP` | No | Dev auto-complete wallet top-up |
| `CORS_ALLOWED_ORIGINS` | Yes | Frontend URLs allowed by CORS |

Generate a secret key:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## Application structure

Each Django app follows a consistent layout:

```
apps/<name>/
├── models.py       # Database models (extend apps.core.BaseModel)
├── serializers.py  # DRF serializers & request/response schemas
├── views.py        # API views (JWT protected by default)
├── urls.py         # URL routing
├── tests.py        # APITestCase integration tests
├── admin.py        # Django admin (optional)
├── utils.py        # Business helpers (optional)
└── migrations/     # Auto-generated DB migrations
```

### Apps

| App | Responsibility |
|-----|----------------|
| `core` | `BaseModel` (UUID pk, timestamps), shared utils |
| `users` | Registration, login, JWT tokens, `UserProfile` |
| `customers` | Rider profile, wallet, payment methods, saved places, emergency contacts |
| `trips` | Trip records (consumed by customer trip-history API) |
| `ratings` | Trip ratings |
| `notifications` | In-app notification feed, FCM device token registration |

### Settings modules

| Module | Use |
|--------|-----|
| `conzura_backend.settings.development` | Local dev (default in `manage.py`) |
| `conzura_backend.settings.production` | Production (`DEBUG=False`) |

Override for production:

```bash
export DJANGO_SETTINGS_MODULE=conzura_backend.settings.production
```

## API endpoints

### Authentication (`/auth/` and `/api/v1/auth/`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `register/` | Create account + JWT tokens |
| POST | `token/` | Login (access + refresh) |
| POST | `token/refresh/` | Refresh access token |

### Customers (`/customers/` and `/api/v1/customers/`)

| Method | Path | Description |
|--------|------|-------------|
| GET/PUT/PATCH | `profile/` | Rider profile |
| GET/POST | `saved-places/` | List / create saved places |
| GET/PUT/DELETE | `saved-places/{id}/` | Saved place detail |
| GET/POST | `payment-methods/` | Payment methods |
| GET | `wallet/` | Wallet balance |
| POST | `wallet/topup/` | Initiate wallet top-up |
| POST | `wallet/topup/verify/` | Verify Razorpay payment |
| GET | `trip-history/` | Paginated trip history |
| GET | `ratings/` | Ratings given / received |

### Notifications (`/notifications/` and `/api/v1/notifications/`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List notifications (unread first) |
| PATCH | `{id}/read/` | Mark one as read |
| POST | `read-all/` | Mark all as read (201) |
| POST | `fcm-token/` | Register FCM device token |

### Documentation

| Path | Description |
|------|-------------|
| `/docs/` | Swagger UI |
| `/redoc/` | ReDoc |
| `/api/schema/` | Raw OpenAPI JSON |

## Development commands

```bash
# Makefile shortcuts (macOS/Linux/WSL with make installed)
make run          # Start server
make test         # Run tests
make migrate      # Apply migrations
make superuser    # Create admin user
make docker-up    # Start Postgres container

# Django management
python manage.py runserver
python manage.py test
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py spectacular --file schema.json
```

## Docker (PostgreSQL only)

```bash
docker compose up -d      # start
docker compose down       # stop
docker compose logs -f db # logs
```

Default credentials match `.env.example` (`postgres` / `postgres`, database `conzura_data`).

## Testing

```bash
python manage.py test
python manage.py test apps.notifications.tests
python manage.py test apps.users.tests apps.customers.tests
```

## Dependencies

| Package | Purpose |
|---------|---------|
| `Django` | Web framework |
| `djangorestframework` | REST API |
| `djangorestframework-simplejwt` | JWT authentication |
| `django-cors-headers` | Frontend CORS |
| `django-filter` | API filtering |
| `drf-spectacular` | Swagger / OpenAPI docs |
| `psycopg2-binary` | PostgreSQL driver |
| `python-decouple` | `.env` configuration |
| `razorpay` | Wallet payments |
| `Pillow` | Image support (future uploads) |

Install:

```bash
pip install -r requirements.txt          # flexible versions
pip install -r requirements.lock.txt     # exact pinned versions (recommended)
```

Verify everything is installed correctly:

```powershell
.\scripts\verify_deps.ps1
```

```bash
chmod +x scripts/verify_deps.sh && ./scripts/verify_deps.sh
```

Expected result: `pip check` passes, all imports succeed, `manage.py check` OK, **34 tests** pass.

Tests use a separate `test_*` database created automatically by Django.

## Security notes for the team

- `.env` is gitignored — share credentials via a secure channel, not Git.
- Use Razorpay **test** keys in development.
- Set `DEBUG=False` and a strong `SECRET_KEY` in production.
- Rotate keys if they are ever committed accidentally.

## Optional: seed data

```bash
# Create Django admin user
python manage.py createsuperuser

# Seed a test trip (if management command exists)
python manage.py seed_test_trip
```

Notifications are created automatically on registration/login (welcome) and wallet top-up.
