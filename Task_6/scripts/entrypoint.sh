#!/bin/bash
set -e

echo "Ждем доступности базы данных $DB_HOST..."
until PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d postgres -c '\q'; do
  >&2 echo "Postgres недоступен, ждем..."
  sleep 3
done

echo "База данных доступна! Запускаем инициализацию..."

# Запускаем скрипт инициализации БД
bash /scripts/init_db.sh

# Применяем миграции Django
bash /scripts/migrate.sh

# Запускаем приложение
exec "$@"
