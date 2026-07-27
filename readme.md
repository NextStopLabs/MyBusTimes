# MyBusTimes
[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC_BY--NC--SA_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
![CodeRabbit Pull Request Reviews](https://img.shields.io/coderabbit/prs/github/NextStopLabs/MyBusTimes?utm_source=oss&utm_medium=github&utm_campaign=NextStopLabs%2FMyBusTimes&labelColor=171717&color=FF570A&link=https%3A%2F%2Fcoderabbit.ai&label=CodeRabbit+Reviews)

MyBusTimes is a Django-based platform for bus route data, live tracking, community features, and admin workflows. This repository includes the web app, API endpoints, admin dashboards, and supporting services.

## Table of Contents
- Overview
- Tech Stack
- Requirements
- Quick Start (Local)
- Environment Variables
- Database Setup (Local Postgres)
- Running the App
- Production Notes
- Optional: Docker Compose (Sanitized)
- Nginx Reference
- Troubleshooting

## Overview
- Public-facing site, community content, and documentation.
- Admin tools for moderation, data imports, and analytics.
- API endpoints for routes, stops, timetables, and tracking.

## Tech Stack
- Python / Django (ASGI)
- Django REST Framework
- PostgreSQL (recommended) or SQLite (local dev)
- Optional: PgBouncer for DB pooling

## Requirements
- Python 3.11.x
- pip
- PostgreSQL 17.x (optional for local, recommended for staging/prod)

## Quick Start (Local)
Create a virtual environment and run with SQLite:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata data.json
python manage.py createsuperuser
python manage.py runserver
```

App will be available at http://localhost:8000

## Environment Variables
Create a `.env` file with at least these values. Use real secrets locally and in prod.

```
DEBUG=True
SECRET_KEY=
ALLOWED_HOSTS=

DB_NAME=mybustimes
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=

CF_SITE_KEY=
CF_SECRET_KEY=

STRIPE_SECRET_KEY=
STRIPE_PUBLISHABLE_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_BILLING_PORTAL_URL=https://billing.stripe.com/

STRIPE_PUBLISHABLE_KEY_TEST=
STRIPE_SECRET_KEY_TEST=
STRIPE_WEBHOOK_SECRET_TEST=

STRIPE_BASIC_MONTHLY_PRICE_ID=
STRIPE_BASIC_YEARLY_PRICE_ID=
STRIPE_BASIC_ONE_OFF_PRICE_ID=
STRIPE_PRO_MONTHLY_PRICE_ID=
STRIPE_PRO_YEARLY_PRICE_ID=
STRIPE_PRO_ONE_OFF_PRICE_ID=

DISCORD_BOT_API_URL=http://localhost:8070
DISCORD_WEB_ERROR_WEBHOOK=
DISCORD_404_ERROR_WEBHOOK=
DISCORD_REPORTS_CHANNEL_ID=
DISCORD_LIVERY_ID=
DISCORD_GAME_ID=
DISCORD_OPERATOR_LOGS_ID=
DISCORD_GUILD_ID=
DISCORD_BOT_API_TOKEN=

SMTP_HOST=
SMTP_PORT=
SMTP_USER=
SMTP_PASSWORD=
```

Notes:
- Add your domain to `CSRF_TRUSTED_ORIGINS` in settings.
- Keep `DEBUG=True` in local dev to bypass captcha checks.

## Database Setup (Local)
To run MBT local you can use sqlite

settings_local.py
```python
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
```

If you prefer PostgreSQL locally:

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib -y
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

Create DB and user:

```bash
sudo -i -u postgres
psql
```

```sql
CREATE USER mybustimesdb WITH PASSWORD 'your_secure_password';
CREATE DATABASE mybustimes OWNER mybustimesdb;
GRANT ALL ON SCHEMA public TO mybustimesdb;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO mybustimesdb;
\q
```

Then set `DB_*` in `.env` and run migrations.

## Running the App
With your venv active:

```bash
python manage.py migrate
python manage.py loaddata data.json
python manage.py runserver
```

## Production Notes
- Set `DEBUG=False` and configure `ALLOWED_HOSTS`.
- Use PostgreSQL.
- Use a reverse proxy (Nginx) in front of ASGI workers.
- Production DB architecture documented internally.

## Optional: Docker Compose (Sanitized)
This is an example snippet to illustrate pooling and health checks. Use your own values.

```
services:
  pgbouncer:
    image: edoburu/pgbouncer:1.23.1
    restart: always
    environment:
      DB_USER:
      DB_PASSWORD:
      DB_HOST: pg17
      DB_NAME:
      POOL_MODE: transaction
      MAX_CLIENT_CONN: 500
      DEFAULT_POOL_SIZE: 32
    ports:
      - "6432:5432"
    depends_on:
      - pg17
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -h pg17 -p 5432 -U ${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    deploy:
      resources:
        limits:
          cpus: '0.50'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  pg17:
    image: postgres:17.2
    shm_size: 2g
    env_file:
      - .env
    command:
      - "postgres"
      - "-c"
      - "max_connections=150"
      - "-c"
      - "shared_buffers=4GB"
      - "-c"
      - "effective_cache_size=12GB"
      - "-c"
      - "maintenance_work_mem=1GB"
      - "-c"
      - "checkpoint_completion_target=0.9"
      - "-c"
      - "wal_buffers=16MB"
      - "-c"
      - "default_statistics_target=100"
      - "-c"
      - "random_page_cost=1.1"
      - "-c"
      - "effective_io_concurrency=200"
      - "-c"
      - "work_mem=32MB"
      - "-c"
      - "huge_pages=off"
      - "-c"
      - "min_wal_size=1GB"
      - "-c"
      - "max_wal_size=4GB"
    ports:
      - "127.0.0.1:5432:5432"
    volumes:
      - pg17-data:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-postgres}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    deploy:
      resources:
        limits:
          cpus: '2.00'
          memory: 6G
        reservations:
          cpus: '1.00'
          memory: 3G
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "5"

volumes:
  pg17-data:
```

## Nginx Reference
Minimal reverse proxy example:

```
server {
    listen 4986;
    server_name example.com;

    client_max_body_size 1G;

    location /static/ {
        alias /srv/MyBusTimes/staticfiles/;
        autoindex off;
    }

    location /media/ {
        alias /srv/MyBusTimes/media/;
        autoindex off;
    }

    location / {
        proxy_pass http://127.0.0.1:5681;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Troubleshooting
- If CSS or media is missing, run `python manage.py collectstatic` and verify file permissions.
- If DB connection fails, confirm `.env` values and Postgres user permissions.
