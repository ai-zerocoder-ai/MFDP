import pytest
from rest_framework import status
from rest_framework.test import APIClient
from PIL import Image

from apps.users.models import TelegramUser
from apps.generations.models import Generation


@pytest.fixture
def api_client():
    """
    DRF-клиент, который корректно обрабатывает multipart/form-data (включая файлы).
    """
    return APIClient()


@pytest.mark.django_db
def test_create_generation_without_image_behaves_gracefully(api_client):
    """
    POST /api/generations/ без файла image → 201 Created (API умеет создавать запись без изображения).
    Проверяем, что ответ 201, в JSON есть id и prompt_en, а в базе появилась нужная запись.
    """
    # 1) Создаём пользователя, чтобы внешний ключ был валиден
    TelegramUser.objects.create(telegram_id=42, tokens=50)

    url = "/api/generations/"
    payload = {
        "prompt_en": "TestPrompt",
        "telegram_id": 42,
        "charge_user": "true",
        # не передаём "image"
    }

    resp = api_client.post(url, data=payload, format="multipart")
    assert resp.status_code == status.HTTP_201_CREATED

    data = resp.json()
    # В ответе должны быть минимум id и prompt_en
    assert "id" in data
    assert data.get("prompt_en") == "TestPrompt"
    # Поле image может отсутствовать или быть пустым
    if "image" in data:
        assert data["image"] in (None, "", [])

    # Проверяем, что в базе появилась запись
    gen = Generation.objects.get(id=data["id"])
    assert gen.prompt_en == "TestPrompt"
    # Пользовательская связь верна
    assert str(gen.user.telegram_id) == "42"


@pytest.mark.django_db
def test_create_generation_with_valid_image(tmp_path, api_client):
    """
    POST /api/generations/ с настоящим PNG → 201 Created.
    Проверяем, что:
      1) статус 201
      2) JSON-ответ содержит id и prompt_en
      3) в БД появилась запись с корректными prompt_en и связью на telegram_id
      4) поле image действительно сохранено
    """
    # 1) Создаём пользователя
    TelegramUser.objects.create(telegram_id=84, tokens=100)

    # 2) Генерируем реальный PNG-файл 1×1 через Pillow
    file_path = tmp_path / "valid.png"
    img = Image.new("RGB", (1, 1), color="white")
    img.save(str(file_path), format="PNG")

    with open(file_path, "rb") as f:
        url = "/api/generations/"
        data = {
            "prompt_en": "AnotherTest",
            "telegram_id": 84,
            "charge_user": "true",
            "image": f,
        }
        resp = api_client.post(url, data=data, format="multipart")

    assert resp.status_code == status.HTTP_201_CREATED

    resp_data = resp.json()
    # В ответе должны быть id и prompt_en
    assert "id" in resp_data
    assert resp_data.get("prompt_en") == "AnotherTest"
    # Не проверяем здесь telegram_id, его нет в JSON

    # Проверяем, что в базе появилась нужная запись
    gen = Generation.objects.get(id=resp_data["id"])
    assert gen.prompt_en == "AnotherTest"
    assert str(gen.user.telegram_id) == "84"

    # Поле image не должно быть пустым (файл сохранился)
    assert gen.image, "Поле image должно содержать путь к файлу"
    assert str(gen.image).lower().endswith(".png")
