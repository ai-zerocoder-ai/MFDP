from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Generation
from .serializers import GenerationSerializer
from apps.users.models import TelegramUser

class GenerationViewSet(viewsets.ModelViewSet):
    queryset = Generation.objects.all()
    serializer_class = GenerationSerializer

    def create(self, request, *args, **kwargs):
        telegram_id = request.data.get('telegram_id')
        if not telegram_id:
            return Response({"detail": "telegram_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Ищем пользователя по telegram_id
        try:
            user = TelegramUser.objects.get(telegram_id=telegram_id)
        except TelegramUser.DoesNotExist:
            return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        # Смотрим, нужно ли списывать токены (charge_user=true для первого файла)
        charge_user = request.data.get('charge_user', 'true') == 'true'
        if charge_user:
            # Проверяем, достаточно ли токенов
            if user.tokens < 10:
                return Response({"detail": "Not enough tokens"}, status=status.HTTP_402_PAYMENT_REQUIRED)
            # Списываем 10 токенов
            user.tokens -= 10
            user.save()

        # Теперь создаём запись Generation.
        # Если у вас поле user в Generation обязательное, укажите его при сохранении
        # Но для этого в сериализаторе user должно быть read_only
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Привязываем user к объекту
        generation = serializer.save(user=user)

        return Response(GenerationSerializer(generation).data, status=status.HTTP_201_CREATED)
