# MyBusTimes V2

## .env setup

```
DEBUG=True
SECRET_KEY=
ALLOWED_HOSTS=127.0.0.1,localhost
STRIPE_SECRET_KEY=
STRIPE_PUBLISHABLE_KEY=
PRICE_ID_MONTHLY=
PRICE_ID_YEARLY=
PRICE_ID_CUSTOM=
STRIPE_WEBHOOK_SECRET=
DISCORD_BOT_TOKEN=
DISCORD_CHANNEL_ID=
``` 

## Setup

### Reqirements
• python 3.11

### Setup
```bash
python3 -m venv mybustimes
```

```bash
source mybustimes/bin/activate
```

```bash
python manage.py makemigrations
python manage.py migrate
```

```bash
python manage.py createsuperuser
```

```bash
python manage.py runserver
```
