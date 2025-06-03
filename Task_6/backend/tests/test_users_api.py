import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import TelegramUser


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_create_and_get_user_via_api(api_client):
    """
    1) POST /api/users/ с новыми данными → 201 CREATED
    2) GET /api/users/?telegram_id=<id> возвращает созданного пользователя
    """
    # 1. Формируем жёсткий URL для списка пользователей
    url_list = "/api/users/"

    # 2. Выполняем POST, чтобы создать нового пользователя
    payload = {
        "telegram_id": 123,
        "tokens": 50,
    }
    resp_post = api_client.post(url_list, data=payload, format="json")
    assert resp_post.status_code == status.HTTP_201_CREATED

    resp_data = resp_post.json()
    # В ответе поле telegram_id приходит строкой, поэтому сравниваем как строку
    assert str(resp_data.get("telegram_id")) == "123"
    assert resp_data.get("tokens") == 50
    assert "id" in resp_data

    # 3. Делаем GET с фильтром по telegram_id
    get_url = f"{url_list}?telegram_id=123"
    resp_get = api_client.get(get_url, format="json")
    assert resp_get.status_code == status.HTTP_200_OK

    data_list = resp_get.json()
    # Ожидаем список из одного пользователя
    assert isinstance(data_list, list)
    assert len(data_list) == 1

    user_data = data_list[0]
    # Снова сравниваем telegram_id как строку
    assert str(user_data.get("telegram_id")) == "123"
    assert user_data.get("tokens") == 50
