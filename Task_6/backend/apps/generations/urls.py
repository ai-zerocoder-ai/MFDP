from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GenerationViewSet

router = DefaultRouter()
router.register(r'', GenerationViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
