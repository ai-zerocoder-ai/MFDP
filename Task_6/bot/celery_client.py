import os
from celery import Celery

# Берём из окружения те же переменные, что и воркер
BROKER = os.getenv("CELERY_BROKER_URL", "")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "")

celery_app = Celery(
    "bot_client",
    broker=BROKER,
    backend=RESULT_BACKEND,
)

# Используем JSON-формат сериализации, как и в воркере
celery_app.conf.update(
    accept_content=["json"],
    task_serializer="json",
    result_serializer="json",
    timezone="UTC",
)
