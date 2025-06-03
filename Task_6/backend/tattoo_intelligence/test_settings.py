from .settings import *  # подтягиваем все остальные настройки

# Заменяем DATABASES на SQLite in-memory, чтобы нигде не лезть в Postgres
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
