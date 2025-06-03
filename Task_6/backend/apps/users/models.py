from django.db import models

class TelegramUser(models.Model):
    telegram_id = models.CharField(max_length=64, unique=True)
    username = models.CharField(max_length=150, blank=True, null=True)
    first_name = models.CharField(max_length=150, blank=True, null=True)
    last_name = models.CharField(max_length=150, blank=True, null=True)

    # Новое поле для хранения токенов (баланса)
    tokens = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.username or str(self.telegram_id)
