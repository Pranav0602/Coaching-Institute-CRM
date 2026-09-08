from rest_framework import serializers
from rag.models import KnowledgeDocument, DocumentChunk, IngestionJob, RagQueryAudit


class KnowledgeDocumentSerializer(serializers.ModelSerializer):
    chunks_count = serializers.IntegerField(source='chunks.count', read_only=True)
    metadata_json = serializers.JSONField(required=False, default=dict)

    class Meta:
        model = KnowledgeDocument
        fields = [
            'id', 'title', 'category', 'content', 'source_url', 
            'branch', 'target_role', 'is_published', 'version', 
            'metadata_json', 'chunks_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RagQueryInputSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=1000, required=True)
    session_id = serializers.CharField(max_length=128, required=False, allow_blank=True)


class RagQueryAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = RagQueryAudit
        fields = [
            'id', 'prompt', 'response_text', 'confidence_score', 
            'response_time_ms', 'user_feedback_rating', 'created_at'
        ]


class IngestionJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = IngestionJob
        fields = '__all__'
