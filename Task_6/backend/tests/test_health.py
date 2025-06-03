import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_health_endpoint(client):
    """
    Проверяем, что GET /health/ возвращает 200 OK.
    """
    # Предположим, в urls.py у вас указано: path("health/", HealthView.as_view(), name="health")
    url = reverse("health")
    response = client.get(url)
    assert response.status_code == 200
    # В зависимости от того, что возвращает ваша implementaion, можно строго проверить body:
    content = response.content.decode().lower()
    assert "ok" in content  # например, "ok" или {"status":"ok"}
