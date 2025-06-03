from django.db import models
from apps.users.models import TelegramUser
import uuid
import os

def user_directory_path(instance, filename):
    """
    Формирует путь для хранения файла, например:
    'generations/123456789/5f7e9d2c-4c90-4df6-a13b-8dbf2bf20a77.png'
    где 123456789 — это telegram_id пользователя, а имя файла заменено на UUID.
    """
    ext = filename.split('.')[-1] if '.' in filename else ''  # Получаем расширение
    telegram_id = instance.user.telegram_id  # Берём telegram_id из связанного пользователя
    new_filename = f"{uuid.uuid4()}.{ext}" if ext else f"{uuid.uuid4()}"
    return f"generations/{telegram_id}/{new_filename}"

class Generation(models.Model):
    user = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name='generations'
    )
    #prompt_ru = models.TextField()
    prompt_en = models.TextField(blank=True, null=True)
    #parameters = models.JSONField(blank=True, null=True)

    # Сохраняем файлы в подпапку, зависящую от пользователя
    image = models.ImageField(upload_to='generations/', blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Generation {self.id} for user {self.user_id}"
