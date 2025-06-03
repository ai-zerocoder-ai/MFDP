import os
import pytest

def pytest_configure(config):
    """
    Срабатывает РАНЬШЕ, чем создаётся тестовая база Django.
    Здесь сразу подменяем DATABASES → SQLite in-memory,
    и выставляем DJANGO_SETTINGS_MODULE, чтобы pytest-django знал, какие settings использовать.
    """
    # 1) Гарантируем, что Django будет применять нужный settings-модуль
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tattoo_intelligence.settings")

    # 2) Подменяем DATABASES['default'] на SQLite in-memory
    from django.conf import settings
    settings.DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
