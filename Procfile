web: cd backend/Services/HelpdeskService && alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8005}
worker: cd backend/Services/HelpdeskService && celery -A celery_app.celery_app worker --loglevel=info
