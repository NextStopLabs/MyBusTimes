FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["gunicorn", "mybustimes.asgi:application", \
    "--workers", "4", \
    "--worker-class", "uvicorn.workers.UvicornWorker", \
    "--bind", "0.0.0.0:8000", \
    "--log-level", "info", \
    "--timeout", "30", \
    "--graceful-timeout", "30", \
    "--max-requests", "1000", \
    "--max-requests-jitter", "200", \
    "--worker-tmp-dir", "/dev/shm"]
