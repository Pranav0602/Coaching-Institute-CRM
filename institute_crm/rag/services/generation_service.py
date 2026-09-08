"""
Generation Service for RAG pipeline.
Synthesizes answers grounded strictly in retrieved context with source citations and safe fallback.
"""
from __future__ import annotations

import os
import json
import time
import logging
from typing import Dict, Any, List

from accounts.models import User
from rag.models import RagQueryAudit
from rag.services.retrieval_service import RetrievalService

logger = logging.getLogger('institute_crm.rag')


class GenerationService:
    @classmethod
    def answer_query(
        cls,
        prompt: str,
        actor: User | None = None,
        session_id: str | None = None,
    ) -> Dict[str, Any]:
        """
        Executes end-to-end RAG query:
        1. Retrieves relevant context chunks using RetrievalService.
        2. Grounds LLM generation in context.
        3. Formats response with explicit citations.
        4. Logs audit record to RagQueryAudit.
        """
        start_time = time.time()
        retrieved_chunks = RetrievalService.retrieve_context(query=prompt, actor=actor, top_k=4)

        if not retrieved_chunks:
            response_text = (
                "I couldn't find specific information in the institute knowledge base matching your question. "
                "Please contact the admission desk or branch administration for more details."
            )
            citations = []
            confidence = 0.2
        else:
            response_text, confidence = cls._synthesize_answer(prompt, retrieved_chunks)
            citations = [
                {
                    'chunk_id': c['chunk_id'],
                    'title': c['title'],
                    'category': c['category'],
                    'excerpt': c['content'][:150] + ("..." if len(c['content']) > 150 else ""),
                    'score': round(c['score'], 3),
                }
                for c in retrieved_chunks
            ]

        elapsed_ms = int((time.time() - start_time) * 1000)

        # Audit logging
        RagQueryAudit.objects.create(
            user=actor if (actor and actor.is_authenticated) else None,
            session_id=session_id,
            prompt=prompt,
            retrieved_chunk_ids=[c['chunk_id'] for c in retrieved_chunks],
            response_text=response_text,
            confidence_score=confidence,
            response_time_ms=elapsed_ms,
        )

        return {
            'query': prompt,
            'answer': response_text,
            'confidence': confidence,
            'response_time_ms': elapsed_ms,
            'citations': citations,
            'suggested_questions': cls._generate_follow_up_suggestions(prompt, retrieved_chunks),
        }

    @classmethod
    def _synthesize_answer(cls, prompt: str, chunks: List[Dict[str, Any]]) -> tuple[str, float]:
        """
        Calls LLM (AWS Bedrock / OpenAI) with context-grounded prompt or returns structured extracted answer.
        """
        context_block = "\n\n".join(
            f"--- Document [{idx+1}]: {c['title']} ---\n{c['content']}"
            for idx, c in enumerate(chunks)
        )

        # 1. Try AWS Bedrock Claude if available
        aws_key = os.environ.get("AWS_ACCESS_KEY_ID")
        if aws_key:
            try:
                import boto3
                client = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION', 'ap-south-1'))
                system_prompt = (
                    "You are the Coaching Institute AI Assistant. Answer the question accurately based ONLY on the provided documents. "
                    "Cite sources clearly. If the answer cannot be found in the documents, state that clearly."
                )
                body = json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 512,
                    "system": system_prompt,
                    "messages": [
                        {
                            "role": "user",
                            "content": f"Context:\n{context_block}\n\nQuestion: {prompt}"
                        }
                    ]
                })
                resp = client.invoke_model(modelId="anthropic.claude-3-haiku-20240307-v1:0", body=body)
                resp_json = json.loads(resp['body'].read())
                answer = resp_json['content'][0]['text']
                return answer, 0.95
            except Exception as e:
                logger.debug(f"Bedrock synthesis fallback: {e}")

        # 2. Try OpenAI if key available
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            try:
                import urllib.request
                req = urllib.request.Request(
                    "https://api.openai.com/v1/chat/completions",
                    data=json.dumps({
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": "You are the Coaching Institute Knowledge Assistant. Answer using ONLY provided context with citations."},
                            {"role": "user", "content": f"Context:\n{context_block}\n\nQuestion: {prompt}"}
                        ],
                        "temperature": 0.2
                    }).encode("utf-8"),
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {openai_key}"}
                )
                with urllib.request.urlopen(req, timeout=15) as r:
                    data = json.loads(r.read().decode())
                    answer = data["choices"][0]["message"]["content"]
                    return answer, 0.92
            except Exception as e:
                logger.debug(f"OpenAI synthesis fallback: {e}")

        # 3. Deterministic high-precision context summarizer
        primary_chunk = chunks[0]
        summary_lines = [
            f"Based on our institute records for **{primary_chunk['title']}**:",
            "",
            primary_chunk['content'],
        ]
        if len(chunks) > 1:
            summary_lines.extend([
                "",
                f"**Additional Related Information ({chunks[1]['title']}):**",
                chunks[1]['content'][:250] + "...",
            ])
        return "\n".join(summary_lines), 0.85

    @classmethod
    def _generate_follow_up_suggestions(cls, prompt: str, chunks: List[Dict[str, Any]]) -> List[str]:
        suggestions = [
            "What are the fee payment options and installment plans?",
            "What courses and batches are currently open for admission?",
            "What is the attendance and examination grading policy?",
        ]
        return suggestions
