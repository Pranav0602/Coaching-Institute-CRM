from django.urls import path, include
from rest_framework.routers import DefaultRouter
from communications.views import (
    AnnouncementViewSet,
    DeviceTokenViewSet,
    NotificationViewSet,
)

router = DefaultRouter()
router.register(r'announcements', AnnouncementViewSet, basename='announcement')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'devices', DeviceTokenViewSet, basename='device')

urlpatterns = [
    path('', include(router.urls)),
]
