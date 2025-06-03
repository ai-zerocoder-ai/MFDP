#!/bin/bash
set -e

# Загрузка переменных окружения из файла .env, расположенного в корне проекта
if [ -f ../.env ]; then
    export $(grep -v '^#' ../.env | xargs)
fi

echo "Инициализация базы данных PostgreSQL..."
echo "Создаем базу данных $DB_NAME..."

# Команда для создания базы данных. Убедитесь, что у пользователя $DB_USER достаточно прав.
PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME;" || {
    echo "Не удалось создать базу данных или она уже существует."
}

echo "База данных $DB_NAME успешно создана (или уже существует)."
