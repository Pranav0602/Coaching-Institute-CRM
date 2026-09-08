"""
HTTP controller layer for the RAG app.
"""
from __future__ import annotations

from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from rag.models import KnowledgeDocument, IngestionJob, RagQueryAudit
from rag.serializers import (
    KnowledgeDocumentSerializer, RagQueryInputSerializer, 
    RagQueryAuditSerializer, IngestionJobSerializer
)
from rag.services import IngestionService, GenerationService
from accounts.permissions import IsBranchAdmin


class RagQueryView(APIView):
    """
    ``POST /api/v1/rag/query/``
    Public & Authenticated knowledge assistant endpoint.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RagQueryInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user if request.user.is_authenticated else None
        result = GenerationService.answer_query(
            prompt=serializer.validated_data['query'],
            actor=user,
            session_id=serializer.validated_data.get('session_id')
        )
        return Response(result, status=status.HTTP_200_OK)


class IngestionTriggerView(APIView):
    """
    ``POST /api/v1/rag/ingest/``
    Triggers catalog and FAQ knowledge base indexing.
    """
    permission_classes = [IsAuthenticated, IsBranchAdmin]

    def post(self, request):
        job = IngestionService.sync_academic_catalogue()
        return Response(IngestionJobSerializer(job).data, status=status.HTTP_202_ACCEPTED)


class KnowledgeDocumentViewSet(viewsets.ModelViewSet):
    """
    ``/api/v1/rag/documents/``
    CRUD for knowledge documents. Restricted to SUPER_ADMIN and BRANCH_ADMIN
    for the editorial control plane; retrieval itself is via the public /rag/query endpoint.
    """
    queryset = KnowledgeDocument.objects.filter(is_deleted=False).prefetch_related('chunks')
    serializer_class = KnowledgeDocumentSerializer
    permission_classes = [IsAuthenticated, IsBranchAdmin]

    def perform_create(self, serializer):
        doc = serializer.save()
        IngestionService.index_document(doc)

    def perform_update(self, serializer):
        doc = serializer.save()
        IngestionService.index_document(doc)


class RagStatsView(APIView):
    """
    ``GET /api/v1/rag/stats/``
    Provides summary statistics of the RAG vector corpus.
    """
    permission_classes = [IsAuthenticated, IsBranchAdmin]

    def get(self, request):
        from rag.models import DocumentChunk
        doc_count = KnowledgeDocument.objects.filter(is_deleted=False).count()
        chunk_count = DocumentChunk.objects.filter(is_deleted=False).count()
        queries_count = RagQueryAudit.objects.count()

        return Response({
            "documents_count": doc_count,
            "chunks_count": chunk_count,
            "queries_served": queries_count,
            "status": "ready"
        })
