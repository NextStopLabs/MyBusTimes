# Use official Python image
FROM python:3.11

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Run migrations and start server
CMD ["gunicorn", "-b", "0.0.0.0:8000", "myproject.wsgi:application", "--workers", "8"]
