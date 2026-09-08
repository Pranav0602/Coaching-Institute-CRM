"""
Data models for the RAG (Retrieval Augmented Generation) knowledge assistant.
"""
from __future__ import annotations

import uuid
from django.db import models
from institute_crm.utils import BaseModel
from accounts.models import User, Branch, Role

try:
    from pgvector.django import VectorField
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False


class KnowledgeDocument(BaseModel):
    CATEGORY_CHOICES = [
        ('COURSE_CATALOGUE', 'Course Catalogue'),
        ('ADMISSION_POLICY', 'Admission & Refund Policy'),
        ('FAQ', 'Frequently Asked Questions'),
        ('BATCH_SCHEDULE', 'Batch Schedule'),
        ('STUDY_GUIDE', 'Study Material / Syllabus'),
        ('GENERAL', 'General Information'),
    ]

    title = models.CharField(max_length=255, db_index=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='GENERAL', db_index=True)
    content = models.TextField()
    source_url = models.URLField(max_length=500, blank=True, null=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name='knowledge_documents')
    target_role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name='knowledge_documents')
    is_published = models.BooleanField(default=True, db_index=True)
    version = models.PositiveIntegerField(default=1)
    metadata_json = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.title} [{self.category}]"


class DocumentChunk(BaseModel):
    document = models.ForeignKey(KnowledgeDocument, on_delete=models.CASCADE, related_name='chunks')
    chunk_index = models.PositiveIntegerField(default=0)
    content = models.TextField()
    token_count = models.PositiveIntegerField(default=0)
    metadata_json = models.JSONField(default=dict, blank=True)
    
    if HAS_PGVECTOR:
        embedding = VectorField(dimensions=1536, null=True, blank=True)
    else:
        embedding = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['document', 'chunk_index']

    def __str__(self):
        return f"Chunk {self.chunk_index} of {self.document.title}"


class IngestionJob(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_type = models.CharField(max_length=50, default='CATALOGUE_SYNC')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    total_chunks = models.PositiveIntegerField(default=0)
    processed_chunks = models.PositiveIntegerField(default=0)
    error_log = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"IngestionJob {self.job_type} ({self.status})"


class RagQueryAudit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='rag_queries')
    session_id = models.CharField(max_length=128, blank=True, null=True, db_index=True)
    prompt = models.TextField()
    retrieved_chunk_ids = models.JSONField(default=list, blank=True)
    response_text = models.TextField()
    confidence_score = models.FloatField(default=0.0)
    response_time_ms = models.PositiveIntegerField(default=0)
    user_feedback_rating = models.SmallIntegerField(null=True, blank=True) # 1 for thumbs up, -1 for thumbs down
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"RAG Query [{self.created_at.strftime('%Y-%m-%d %H:%M')}] {self.prompt[:40]}..."
