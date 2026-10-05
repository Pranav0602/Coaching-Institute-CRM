from django.urls import path, include
from rest_framework.routers import DefaultRouter
from communications.views import (
    AnnouncementViewSet,
    DeviceTokenViewSet,
    NotificationViewSet,
    TemplateListView,
)
from communications.webhooks import MockWebhookView, WhatsAppWebhookView

router = DefaultRouter()
router.register(r'announcements', AnnouncementViewSet, basename='announcement')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'devices', DeviceTokenViewSet, basename='device')

urlpatterns = [
    path('', include(router.urls)),
    path('templates/', TemplateListView.as_view(), name='whatsapp_templates'),
    path('webhooks/whatsapp/', WhatsAppWebhookView.as_view(), name='whatsapp_webhook'),
    path('mock-webhook/', MockWebhookView.as_view(), name='whatsapp_mock_webhook'),
]
