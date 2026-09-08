from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rag.views import (
    RagQueryView, IngestionTriggerView, KnowledgeDocumentViewSet, RagStatsView
)

router = DefaultRouter()
router.register(r'documents', KnowledgeDocumentViewSet, basename='rag-document')

urlpatterns = [
    path('query/', RagQueryView.as_view(), name='rag_query'),
    path('ingest/', IngestionTriggerView.as_view(), name='rag_ingest'),
    path('stats/', RagStatsView.as_view(), name='rag_stats'),
    path('', include(router.urls)),
]
