"""
Retrieval Service for RAG pipeline.
Executes hybrid vector similarity search and keyword matching with role and branch authorization guardrails.
"""
from __future__ import annotations

import math
import logging
from typing import List, Dict, Any
from django.db.models import Q

from accounts.models import User, Role
from rag.models import DocumentChunk, KnowledgeDocument
from rag.services.embedding_service import EmbeddingService

logger = logging.getLogger('institute_crm.rag')


class RetrievalService:
    @classmethod
    def retrieve_context(
        cls,
        query: str,
        actor: User | None = None,
        top_k: int = 4,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top_k most relevant document chunks for the given query,
        strictly respecting the user's role and branch permissions.
        """
        query = query.strip()
        if not query:
            return []

        # 1. Base scoping filter
        doc_filter = Q(document__is_published=True, document__is_deleted=False)

        if actor and actor.is_authenticated and actor.role:
            role_code = actor.role.code
            if role_code not in [Role.SUPER_ADMIN]:
                # Branch isolation: document must have no specific branch or match actor's branch
                if actor.branch:
                    doc_filter &= Q(document__branch__isnull=True) | Q(document__branch=actor.branch)
                else:
                    doc_filter &= Q(document__branch__isnull=True)

                # Role isolation: document must have no target role or match actor's role
                doc_filter &= Q(document__target_role__isnull=True) | Q(document__target_role=actor.role)
        else:
            # Anonymous / prospective users: only general public documents
            doc_filter &= Q(document__branch__isnull=True) & Q(document__target_role__isnull=True)

        chunks_qs = DocumentChunk.objects.filter(doc_filter).select_related('document')

        # 2. Generate Query Embedding
        query_embedding = EmbeddingService.get_embedding(query)

        # 3. Hybrid search: vector cosine similarity + keyword boost
        scored_chunks = []
        query_terms = set(query.lower().split())

        for chunk in chunks_qs:
            score = 0.0

            # Vector similarity calculation
            if chunk.embedding and len(chunk.embedding) == len(query_embedding):
                dot_product = sum(a * b for a, b in zip(chunk.embedding, query_embedding))
                score += dot_product * 0.75

            # Keyword lexical matching boost
            content_lower = chunk.content.lower()
            title_lower = chunk.document.title.lower()
            term_matches = sum(1 for term in query_terms if term in content_lower or term in title_lower)
            if query_terms:
                keyword_score = term_matches / len(query_terms)
                score += keyword_score * 0.25

            scored_chunks.append({
                'chunk_id': str(chunk.id),
                'document_id': str(chunk.document.id),
                'title': chunk.document.title,
                'category': chunk.document.category,
                'content': chunk.content,
                'score': score,
                'metadata': chunk.metadata_json,
            })

        # 4. Sort by score descending and take top_k
        scored_chunks.sort(key=lambda x: x['score'], reverse=True)
        return scored_chunks[:top_k]
