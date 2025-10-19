# MyBusTimes V2
[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC_BY--NC--SA_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)

# Important notes
1. add your doimain to settings "CSRF_TRUSTED_ORIGINS"
2. Keep debug enabled to disable captcha
3. Only test on python 3.11.0

## .env setup

```
DEBUG=True
SECRET_KEY=
ALLOWED_HOSTS=

STRIPE_SECRET_KEY=sk_live_
STRIPE_PUBLISHABLE_KEY=pk_live_
STRIPE_WEBHOOK_SECRET=
STRIPE_BILLING_PORTAL_URL=https://billing.stripe.com/

STRIPE_PUBLISHABLE_KEY_TEST=pk_test_
STRIPE_SECRET_KEY_TEST=sk_test_
STRIPE_WEBHOOK_SECRET_TEST=

PRICE_ID_MONTHLY=price_
PRICE_ID_YEARLY=price_
PRICE_ID_CUSTOM=price_

PRICE_ID_MONTHLY_TEST=price_
PRICE_ID_YEARLY_TEST=price_
PRICE_ID_CUSTOM_TEST=price_

DISCORD_LIVERY_REQUESTS_CHANNEL_WEBHOOK=https://discord.com/api/webhooks/
DISCORD_OPERATOR_TYPE_REQUESTS_CHANNEL_WEBHOOK=https://discord.com/api/webhooks/
DISCORD_TYPE_REQUEST_WEBHOOK=https://discord.com/api/webhooks/
DISCORD_FOR_SALE_WEBHOOK=https://discord.com/api/webhooks/
DISCORD_WEB_ERROR_WEBHOOK=https://discord.com/api/webhooks/
DISCORD_404_ERROR_WEBHOOK=https://discord.com/api/webhooks/
DISCORD_BOT_API_URL=http://localhost:8080

DISCORD_GUILD_ID=
DISCORD_BOT_API_TOKEN=

DISCORD_MIGRATION_ERROR_ID=
DISCORD_REPORTS_CHANNEL_ID=
DISCORD_LIVERY_ID=
DISCORD_GAME_ID=
DISCORD_OPERATOR_LOGS_ID=

DISCORD_GUILD_ID=
DISCORD_BOT_API_TOKEN=

DB_NAME=mybustimes
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=

SMTP_HOST=
SMTP_PORT=
SMTP_USER=
SMTP_PASSWORD=

CF_SITE_KEY=
CF_SECRET_KEY=
``` 

# Local Dev
## Inishel Setup

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

Then run the server
```bash
python manage.py runserver
```

Now it should be all setup and accessable from http://localhost:8000

# Setup

## DB Setup - Postgress

Update system
```bash
sudo apt update
sudo apt upgrade -y
```

Install postgres
```bash
sudo apt install postgresql postgresql-contrib nginx python3.11 python3.11-venv redis -y
```

Enable and start the service
```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
sudo systemctl enable redis
sudo systemctl start redis
```

Change to the postgres user
```bash
sudo -i -u postgres
```

Enter postgres
```bash
psql
```

Create the user and the db
```sql
CREATE USER mybustimesdb WITH PASSWORD 'your_secure_password';
CREATE DATABASE mybustimes OWNER mybustimesdb;
\c mybustimes
GRANT ALL ON SCHEMA public TO mybustimesdb;
ALTER SCHEMA public OWNER TO mybustimesdb;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO mybustimesdb;
ALTER USER mybustimesdb CREATEDB;
\q
```

Go back to the main user
```bash
exit
```

Test the connection
```bash
psql -h localhost -U username -d dbname
```

Exit if it worked
```
\q
```


## Web setup

Create the python venv
```bash
python3 -m venv .venv
```

Activate the venv
```bash
source .venv/bin/activate
```

Install python dependencies
```bash
pip install -r requirements.txt
```

Migrate main
```bash
python manage.py makemigrations
python manage.py migrate
```

Import base data
```bash
python manage.py loaddata data.json
```

Make your superuser
```bash
python manage.py createsuperuser
```

Create the service file
```bash
sudo nano /etc/systemd/system/mybustimes.service
```

Web service running on port 5681
```bash
[Unit]
Description=My Bus Times Django ASGI HTTP Workers (Gunicorn + Uvicorn)
After=network.target

[Service]
User=mybustimes
Group=mybustimes
WorkingDirectory=/srv/MyBusTimes
Environment="PATH=/srv/MyBusTimes/.venv/bin"
Environment="PYTHONUNBUFFERED=1"

ExecStart=/srv/MyBusTimes/.venv/bin/gunicorn \
    mybustimes.asgi:application \
    --workers 10 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:5681 \
    --log-level info \
    --access-logfile - \
    --error-logfile -

Restart=always
RestartSec=5
LimitNOFILE=4096
TimeoutStopSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Websocket running on port 5682
```bash
[Unit]
Description=My Bus Times Django ASGI WebSocket Worker
After=network.target

[Service]
User=mybustimes
Group=mybustimes
WorkingDirectory=/srv/MyBusTimes
Environment="PATH=/srv/MyBusTimes/.venv/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStart=/srv/MyBusTimes/.venv/bin/uvicorn \
    mybustimes.asgi:application \
    --workers 1 \
    --host 127.0.0.1 \
    --port 5682 \
    --ws websockets \
    --log-level debug \
    --proxy-headers

Restart=always
RestartSec=5
LimitNOFILE=4096
TimeoutStopSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Reload Daemon
```bash
systemctl daemon-reload
```

Enable and start the web service
```bash
sudo systemctl start mybustimes
sudo systemctl start mybustimes-ws
sudo systemctl enable mybustimes
sudo systemctl enable mybustimes-ws
```

Check if its running
```bash
sudo systemctl status mybustimes
```

You show now be able to access it on http://localhost:5681
No styles will be loaded yet

## Setup Nginx
```bash
sudo nano /etc/nginx/sites-available/mybustimes
```

```bash
server {
    listen 4986;
    server_name mybustimes.cc www.mybustimes.cc;

    client_max_body_size 1G;

    # Static files
    location /static/ {
        alias /srv/MyBusTimes/staticfiles/;
        autoindex off;
    }

    # Media files
    location /media/ {
        alias /srv/MyBusTimes/media/;
        autoindex off;
    }

    error_page 502 /502.html;

    location = /502.html {
        root /usr/share/nginx/html;
        internal;
    }

    location /message/ws/ {
        proxy_pass http://127.0.0.1:5682;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;

        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
    }

    # Main proxy to frontend
    location / {
        proxy_pass http://127.0.0.1:5681;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Grant Nginx permitions to access mybustimes files
```bash
sudo chown -R your-user:www-data /path/to/MyBusTimes/staticfiles /path/to/MyBusTimes/media
sudo chmod -R 755 /path/to/MyBusTimes/staticfiles /path/to/MyBusTimes/media
sudo chmod +x /path/to/MyBusTimes
sudo chmod -R o+rx /path/to/MyBusTimes/staticfiles
sudo chmod -R o+rx /path/to/MyBusTimes/media
```

Reload Nginx
```bash
sudo ln -s /etc/nginx/sites-available/mybustimes /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

Now it should be all setup and accessable from http://localhost