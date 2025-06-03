from django.contrib import admin
from django.urls import path, include
from . import health

# Новые импорты для раздачи медиа в режиме отладки
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/users/', include('apps.users.urls')),
    path('api/generations/', include('apps.generations.urls')),
    path('health/', health.health, name='health'),
]

# Раздача /media/ в режиме DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
