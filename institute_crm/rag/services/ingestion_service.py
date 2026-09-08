"""
Ingestion Service for RAG pipeline.
Handles chunking, text normalization, and vector database indexing.
"""
from __future__ import annotations

import re
import logging
from typing import List, Dict, Any
from django.db import transaction
from django.utils import timezone

from rag.models import KnowledgeDocument, DocumentChunk, IngestionJob
from rag.services.embedding_service import EmbeddingService
from academics.models import Course, Batch, Subject

logger = logging.getLogger('institute_crm.rag')


class IngestionService:
    CHUNK_SIZE = 500 # Approximate words
    CHUNK_OVERLAP = 100

    @classmethod
    def chunk_text(cls, text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
        """
        Splits text into chunks with sliding window overlap while preserving sentence boundaries.
        """
        sentences = re.split(r'(?<=[.?!])\s+', text)
        chunks = []
        current_chunk = []
        current_word_count = 0

        for sentence in sentences:
            words = sentence.split()
            sentence_word_count = len(words)

            if current_word_count + sentence_word_count > chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                # Keep overlap sentences
                overlap_words = 0
                overlap_sentences = []
                for s in reversed(current_chunk):
                    s_words = len(s.split())
                    if overlap_words + s_words <= overlap:
                        overlap_sentences.insert(0, s)
                        overlap_words += s_words
                    else:
                        break
                current_chunk = overlap_sentences
                current_word_count = overlap_words

            current_chunk.append(sentence)
            current_word_count += sentence_word_count

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks if chunks else [text]

    @classmethod
    @transaction.atomic
    def index_document(cls, document: KnowledgeDocument) -> int:
        """
        Chunks and creates embeddings for a single KnowledgeDocument.
        """
        # Remove existing chunks
        document.chunks.all().delete()

        chunks_text = cls.chunk_text(document.content)
        created_count = 0

        for idx, chunk_text in enumerate(chunks_text):
            if not chunk_text.strip():
                continue
            
            embedding = EmbeddingService.get_embedding(chunk_text)
            token_count = len(chunk_text.split())

            DocumentChunk.objects.create(
                document=document,
                chunk_index=idx,
                content=chunk_text,
                token_count=token_count,
                embedding=embedding,
                metadata_json={
                    'title': document.title,
                    'category': document.category,
                    'branch_id': str(document.branch_id) if document.branch_id else None,
                    'target_role_id': str(document.target_role_id) if document.target_role_id else None,
                }
            )
            created_count += 1

        logger.info(f"Indexed document '{document.title}' ({created_count} chunks)")
        return created_count

    @classmethod
    def sync_academic_catalogue(cls) -> IngestionJob:
        """
        Automatically ingests courses, subjects, batches, and institute policies into the RAG corpus.
        """
        job = IngestionJob.objects.create(job_type='ACADEMIC_CATALOGUE_SYNC', status='RUNNING')
        try:
            total_chunks = 0
            # 1. Ingest Courses
            courses = Course.objects.filter(is_deleted=False).prefetch_related('subjects')
            for course in courses:
                subjects_list = ", ".join(s.name for s in course.subjects.all()) or "None specified"
                content = f"""
                Course Title: {course.title} (Code: {course.code})
                Duration: {course.duration_weeks} weeks
                Course Description: {course.description or 'Comprehensive coaching curriculum.'}
                Subjects Covered: {subjects_list}
                """
                doc, _ = KnowledgeDocument.objects.update_or_create(
                    title=f"Course: {course.title}",
                    category='COURSE_CATALOGUE',
                    defaults={
                        'content': content.strip(),
                        'metadata_json': {'course_id': str(course.id), 'code': course.code}
                    }
                )
                total_chunks += cls.index_document(doc)

            # 2. Ingest Standard FAQ & Policies if not present
            faqs = [
                (
                    "Admission and Enrollment Process FAQ",
                    "ADMISSION_POLICY",
                    """
                    Admission Policy & Process:
                    1. Prospective students can submit an online enquiry form or visit the nearest branch.
                    2. Admission counselors evaluate prerequisites and recommend suitable batches.
                    3. Fee payments can be made in full or through scheduled installments.
                    4. Once admitted, students receive portal credentials, enrollment number, and access to LMS study materials.
                    Refund Policy: Full refund within 7 days of batch start date minus registration fee (10%). No refunds after 14 days.
                    """
                ),
                (
                    "Fee Payment and Installments Guide",
                    "FAQ",
                    """
                    Fee Structure and Payment Modes:
                    - Payments are accepted via UPI, Net Banking, Credit/Debit Cards, and Bank Transfer.
                    - Installments are spaced at 30-day intervals.
                    - Late fee of INR 50 per day applies on overdue installments after a 5-day grace period.
                    - Digital receipts are automatically generated and sent via email upon payment.
                    """
                ),
                (
                    "Attendance and Examination Rules",
                    "FAQ",
                    """
                    Attendance & Grading Standards:
                    - Minimum 75% attendance is required to be eligible for final certification exams.
                    - Attendance is marked daily by teachers for each lecture session.
                    - Assignments are submitted through the portal and evaluated out of 100.
                    - Letter Grades: A+ (90-100%), A (80-89%), B (70-79%), C (60-69%), D (40-59%), F (Below 40%).
                    """
                )
            ]

            for title, category, content in faqs:
                doc, _ = KnowledgeDocument.objects.update_or_create(
                    title=title,
                    category=category,
                    defaults={'content': content.strip()}
                )
                total_chunks += cls.index_document(doc)

            job.status = 'COMPLETED'
            job.total_chunks = total_chunks
            job.processed_chunks = total_chunks
            job.finished_at = timezone.now()
            job.save()

        except Exception as e:
            logger.error(f"Ingestion job failed: {e}")
            job.status = 'FAILED'
            job.error_log = str(e)
            job.finished_at = timezone.now()
            job.save()

        return job
