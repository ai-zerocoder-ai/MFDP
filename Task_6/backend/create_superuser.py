#!/usr/bin/env python
import os
import django
from django.contrib.auth import get_user_model

# Настройка переменной окружения для Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tattoo_intelligence.settings")
django.setup()

User = get_user_model()

# Чтение параметров суперпользователя из переменных окружения с дефолтными значениями
username = os.environ.get("SUPERUSER_USERNAME", "admin")
email = os.environ.get("SUPERUSER_EMAIL", "admin@example.com")
password = os.environ.get("SUPERUSER_PASSWORD", "admin")

if not User.objects.filter(username=username).exists():
    print("Создаю суперпользователя...")
    User.objects.create_superuser(username=username, email=email, password=password)
else:
    print("Суперпользователь уже существует.")
