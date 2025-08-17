# MyBusTimes V2

## .env setup

```
DEBUG=False
SECRET_KEY=
ALLOWED_HOSTS=

STRIPE_SECRET_KEY=sk_live_
STRIPE_PUBLISHABLE_KEY=pk_live_
STRIPE_WEBHOOK_SECRET=

STRIPE_PUBLISHABLE_KEY_TEST=pk_test_
STRIPE_SECRET_KEY_TEST=sk_test_
STRIPE_WEBHOOK_SECRET_TEST=

PRICE_ID_MONTHLY=price_
PRICE_ID_YEARLY=price_
PRICE_ID_CUSTOM=price_

PRICE_ID_MONTHLY_TEST=price_
PRICE_ID_YEARLY_TEST=price_
PRICE_ID_CUSTOM_TEST=price_

DISCORD_BOT_TOKEN=
DISCORD_REPORTS_CHANNEL_ID=

DISCORD_LIVERY_REQUESTS_CHANNEL_WEBHOOK=https://discord.com/api/webhooks/
DISCORD_OPERATOR_TYPE_REQUESTS_CHANNEL_WEBHOOK=https://discord.com/api/webhooks/
DISCORD_TYPE_REQUEST_WEBHOOK=https://discord.com/api/webhooks/
DISCORD_FOR_SALE_WEBHOOK=https://discord.com/api/webhooks/

DB_NAME=mybustimes
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=

SMTP_HOST=
SMTP_PORT=
SMTP_USER=
SMTP_PASSWORD=
``` 

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
Description=My Bus Times Django Service
After=network.target

[Service]
User=your-user
Group=your-group
WorkingDirectory=/path/to/MyBusTimes
Environment="PATH=/path/to/MyBusTimes/.venv/bin"
ExecStart=/path/to/MyBusTimes/.venv/bin/gunicorn \
    --workers 12 \
    --bind 0.0.0.0:5681 \
    mybustimes.wsgi:application

Restart=always

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
sudo systemctl enable mybustimes
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
    listen 80;
    server_name mybustimes.cc www.mybustimes.cc 127.0.0.1;

    # Static files
    location /static/ {
        alias /path/to/MyBusTimes/staticfiles/;
        autoindex off;
    }

    # Media files
    location /media/ {
        alias /path/to/MyBusTimes/media/;
        autoindex off;
    }

    # Main proxy to Gunicorn
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