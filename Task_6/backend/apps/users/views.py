from rest_framework import viewsets
from .models import TelegramUser
from .serializers import TelegramUserSerializer

class TelegramUserViewSet(viewsets.ModelViewSet):
    queryset = TelegramUser.objects.all()
    serializer_class = TelegramUserSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        telegram_id = self.request.query_params.get('telegram_id')
        if telegram_id:
            qs = qs.filter(telegram_id=telegram_id)
        return qs
