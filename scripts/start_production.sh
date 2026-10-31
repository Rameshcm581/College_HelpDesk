#!/usr/bin/env bash
set -e

# Automatically find Services/HelpdeskService regardless of current working directory
if [ -d "backend/Services/HelpdeskService" ]; then
    cd backend/Services/HelpdeskService
elif [ -d "Services/HelpdeskService" ]; then
    cd Services/HelpdeskService
else
    echo "Could not find Services/HelpdeskService directory!"
    exit 1
fi

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting Uvicorn on port ${PORT:-8005}..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8005}"
