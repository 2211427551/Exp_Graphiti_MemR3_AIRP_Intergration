#!/bin/bash

# Start script for DeepSeek API service

# Load environment variables
set -a
source .env
set +a

# Default values
HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8000}
WORKERS=${WORKERS:-1}
LOG_LEVEL=${LOG_LEVEL:-info}

echo "Starting ${APP_NAME} v${APP_VERSION}"
echo "Host: ${HOST}"
echo "Port: ${PORT}"
echo "Workers: ${WORKERS}"
echo "Debug: ${DEBUG}"

# Start application
uvicorn app.main:app \
    --host ${HOST} \
    --port ${PORT} \
    --workers ${WORKERS} \
    --log-level ${LOG_LEVEL} \
    --reload ${DEBUG}
