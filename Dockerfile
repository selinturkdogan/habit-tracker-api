# Use a slim Python base image
FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set the working folder inside the container
WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the full application code
COPY . .

# Expose the port uvicorn will run on
EXPOSE 8000

# Run migrations, then start the server
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000