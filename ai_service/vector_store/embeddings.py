"""
Embedding Provider Abstraction for Task 7.
Supports pluggable embedding engines:
- GeminiEmbeddingProvider: Google GenAI text-embedding API
- MockEmbeddingProvider: Deterministic offline unit-normalized vectors for testing
- Factory function reading environment configuration
"""

from abc import ABC, abstractmethod
import hashlib
import math
import os
from typing import List, Optional
import httpx

from ai_service.config import Settings, get_settings
from ai_service.logging_config import logger


class BaseEmbeddingProvider(ABC):
    """Abstract base class for vector embedding generation."""

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generates embedding vectors for a list of document chunk texts."""
        pass

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """Generates an embedding vector for a single search query."""
        pass


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """
    Deterministic pseudo-embedding provider for local testing and offline development.
    Generates 128-dimensional unit-normalized vectors ($L_2$ norm = 1.0) using
    term-frequency hashing. Matching tokens produce mathematically consistent
    cosine similarity without requiring external APIs or incurring cost.
    """

    def __init__(self, dimension: int = 128):
        self.dimension = dimension

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._generate_vector(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._generate_vector(text)

    def _generate_vector(self, text: str) -> List[float]:
        vec = [0.0] * self.dimension
        tokens = text.lower().split()

        if not tokens:
            return vec

        for tok in tokens:
            # Hash token to a bucket in [0, dimension - 1]
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
            bucket = h % self.dimension
            sign = 1.0 if (h % 2 == 0) else -1.0
            vec[bucket] += sign * (1.0 + len(tok) * 0.1)

        # L2-normalize vector to unit length
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 1e-9:
            vec = [round(v / norm, 6) for v in vec]

        return vec


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """
    Google Gemini Embedding Provider.
    Invokes the Google GenAI text-embedding REST API (models/text-embedding-004)
    when configured with a valid GEMINI_API_KEY. Falls back to deterministic
    embeddings when no API key is available.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "models/text-embedding-004",
        timeout_seconds: float = 30.0,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.fallback = MockEmbeddingProvider()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not self.api_key:
            logger.info("No GEMINI_API_KEY configured for embeddings. Using deterministic provider.")
            return self.fallback.embed_documents(texts)

        results: List[List[float]] = []
        # Process in batches of 16
        batch_size = 16
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_vectors = self._embed_batch_rest(batch)
            results.extend(batch_vectors)
        return results

    def embed_query(self, text: str) -> List[float]:
        if not self.api_key:
            return self.fallback.embed_query(text)
        vecs = self._embed_batch_rest([text])
        return vecs[0] if vecs else self.fallback.embed_query(text)

    def _embed_batch_rest(self, texts: List[str]) -> List[List[float]]:
        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/{self.model_name}:batchEmbedContents?key={self.api_key}"
        )
        requests_payload = [
            {"model": self.model_name, "content": {"parts": [{"text": t}]}} for t in texts
        ]

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                resp = client.post(endpoint, json={"requests": requests_payload})

            if resp.status_code == 200:
                data = resp.json()
                embeddings_data = data.get("embeddings", [])
                return [e.get("values", []) for e in embeddings_data]
            else:
                logger.warning(f"Gemini embedding API returned {resp.status_code}; using fallback")
                return self.fallback.embed_documents(texts)
        except Exception as exc:
            logger.warning(f"Gemini embedding call failed ({exc}); using fallback")
            return self.fallback.embed_documents(texts)


def get_embedding_provider(settings: Optional[Settings] = None) -> BaseEmbeddingProvider:
    """Factory function returning the configured embedding provider."""
    cfg = settings or get_settings()
    provider_name = (cfg.EMBEDDING_PROVIDER or "gemini").lower().strip()

    if provider_name in ["mock", "testing", "rulebased"]:
        return MockEmbeddingProvider()

    if provider_name in ["gemini", "google"]:
        return GeminiEmbeddingProvider(model_name=cfg.EMBEDDING_MODEL_NAME)

    return MockEmbeddingProvider()
