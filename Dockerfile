# Dockerfile for YouTube Subscriptions Monitor
FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Expose port (default, can be overridden)
ARG FASTAPI_PORT=8088
ENV FASTAPI_PORT=${FASTAPI_PORT}
EXPOSE ${FASTAPI_PORT}

# Entrypoint script to use port from env
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $FASTAPI_PORT"]
