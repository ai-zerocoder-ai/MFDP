# apps/generations/serializers.py
from rest_framework import serializers
from .models import Generation

class GenerationSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)  # поле не изменяется клиентом
    prompt_en = serializers.CharField(allow_blank=True, required=False)

    class Meta:
        model = Generation
        fields = '__all__'
