from django.contrib import admin
from .models import Generation

@admin.register(Generation)
class GenerationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "prompt_en", "created_at")
