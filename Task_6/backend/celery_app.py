import os
from celery import Celery

# Задаём Django-settings для Celery
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tattoo_intelligence.settings")

app = Celery("tattoo_intelligence")

# Читаем настройки из секции CELERY_ в settings.py
app.config_from_object("django.conf:settings", namespace="CELERY")

# Автоматически ищем задачи внутри каждого приложения
app.autodiscover_tasks()
