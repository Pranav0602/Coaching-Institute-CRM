"""
Embedding Service for RAG pipeline.
Generates 1536-dimensional vector embeddings with support for AWS Bedrock Titan, OpenAI, or a deterministic vector fallback.
"""
from __future__ import annotations

import os
import math
import hashlib
import logging
from typing import List

logger = logging.getLogger('institute_crm.rag')


class EmbeddingService:
    EMBEDDING_DIM = 1536

    @classmethod
    def get_embedding(cls, text: str) -> List[float]:
        """
        Generates embedding vector for a given text snippet.
        """
        text = text.strip()
        if not text:
            return [0.0] * cls.EMBEDDING_DIM

        # 1. Try AWS Bedrock if configured
        aws_key = os.environ.get("AWS_ACCESS_KEY_ID")
        if aws_key:
            try:
                import boto3
                import json
                client = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION', 'ap-south-1'))
                response = client.invoke_model(
                    modelId="amazon.titan-embed-text-v1",
                    body=json.dumps({"inputText": text})
                )
                res_body = json.loads(response['body'].read())
                embedding = res_body.get('embedding', [])
                if len(embedding) == cls.EMBEDDING_DIM:
                    return embedding
            except Exception as e:
                logger.debug(f"Bedrock embedding fallback: {e}")

        # 2. Try OpenAI if API key provided
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            try:
                import urllib.request
                import json
                req = urllib.request.Request(
                    "https://api.openai.com/v1/embeddings",
                    data=json.dumps({
                        "input": text,
                        "model": "text-embedding-3-small"
                    }).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {openai_key}"
                    }
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode())
                    return data["data"][0]["embedding"]
            except Exception as e:
                logger.debug(f"OpenAI embedding fallback: {e}")

        # 3. Deterministic semantic pseudo-vector for local development/testing
        return cls._generate_deterministic_vector(text)

    @classmethod
    def _generate_deterministic_vector(cls, text: str) -> List[float]:
        """
        Generates a normalized 1536-dim deterministic vector using token hashing
        so similar tokens produce measurable cosine similarity.
        """
        tokens = text.lower().split()
        vec = [0.0] * cls.EMBEDDING_DIM

        for token in tokens:
            # Hash token to multiple dimensions
            h = int(hashlib.md5(token.encode('utf-8')).hexdigest(), 16)
            for i in range(16):
                idx = (h + i * 97) % cls.EMBEDDING_DIM
                val = (((h >> (i * 4)) & 0xFF) - 128) / 128.0
                vec[idx] += val

        # Normalize vector
        magnitude = math.sqrt(sum(x * x for x in vec))
        if magnitude > 0:
            vec = [x / magnitude for x in vec]
        else:
            vec[0] = 1.0

        return vec
