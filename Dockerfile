FROM python:3.11.11

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p /app/instance

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Expose the port
EXPOSE 5000

# Run the application with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:create_app()"] 