#!/bin/bash
set -e

# Убедимся, что мы в правильной директории
cd /app/backend

echo "Применяем миграции Django..."
python manage.py makemigrations users generations
python3 manage.py migrate

echo "Миграции успешно применены."
