"""Text embedding providers for semantic search.

Default provider is fastembed (ONNX) running a multilingual MiniLM model
on-device. No API keys required, no network after first model download.
Alternative providers (Gemini API, etc.) are pluggable via the
``EmbeddingProvider`` ABC.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable

import numpy as np


class EmbeddingProvider(ABC):
    """Abstract embedding model. Implementations must return L2-normalised vectors."""

    @abstractmethod
    def embed(self, texts: Iterable[str]) -> np.ndarray:
        """Return a (N, D) float32 numpy array of L2-normalised embeddings."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable identifier used as the storage key (e.g. ``local:bge-small-en``)."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Embedding dimensionality."""


class FastembedProvider(EmbeddingProvider):
    """Local on-device embeddings via fastembed (ONNX runtime)."""

    DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    def __init__(self, model_name: str | None = None, cache_dir: "str | Path | None" = None):
        from fastembed import TextEmbedding

        self._model_name = model_name or self.DEFAULT_MODEL
        kwargs: dict = {"model_name": self._model_name}
        if cache_dir is not None:
            kwargs["cache_dir"] = str(cache_dir)
        self._model = TextEmbedding(**kwargs)
        self._dimension = int(self._model.embedding_size)

    def embed(self, texts: Iterable[str]) -> np.ndarray:
        text_list = list(texts)
        if not text_list:
            return np.empty((0, self._dimension), dtype=np.float32)
        # fastembed already L2-normalises for the supported sentence-transformer models.
        vectors = np.asarray(list(self._model.embed(text_list)), dtype=np.float32)
        # Defensive: re-normalise to guard against models that return un-normalised output.
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vectors / norms

    @property
    def name(self) -> str:
        return f"local:{self._model_name}"

    @property
    def dimension(self) -> int:
        return self._dimension


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Embeddings via the Gemini API (``text-embedding-004`` by default)."""

    DEFAULT_MODEL = "text-embedding-004"

    def __init__(self, api_key: str, model_name: str | None = None):
        if not api_key:
            raise ValueError("GeminiEmbeddingProvider requires a Gemini API key")
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model_name = model_name or self.DEFAULT_MODEL
        self._dimension = 768  # text-embedding-004 fixed dimension

    def embed(self, texts: Iterable[str]) -> np.ndarray:
        text_list = list(texts)
        if not text_list:
            return np.empty((0, self._dimension), dtype=np.float32)
        response = self._client.models.embed_content(
            model=self._model_name,
            contents=text_list,
        )
        vectors = np.asarray([e.values for e in response.embeddings], dtype=np.float32)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vectors / norms

    @property
    def name(self) -> str:
        return f"gemini:{self._model_name}"

    @property
    def dimension(self) -> int:
        return self._dimension


def build_provider(
    provider: str,
    model_name: str | None,
    api_key: str = "",
    cache_dir: str | Path | None = None,
) -> EmbeddingProvider:
    """Factory: build the configured embedding provider."""
    provider = provider.lower()
    if provider == "local":
        return FastembedProvider(model_name, cache_dir=cache_dir)
    if provider == "gemini":
        return GeminiEmbeddingProvider(api_key=api_key, model_name=model_name)
    raise ValueError(f"Unknown embedding provider: {provider!r}")


_cached_default: EmbeddingProvider | None = None


def get_default_provider() -> EmbeddingProvider:
    """Return the process-wide embedder instance built from current settings.

    Caches the loaded model so successive pipeline runs and search requests
    don't re-download / re-instantiate it.
    """
    global _cached_default
    if _cached_default is not None:
        return _cached_default
    from tube_agent.config import get_settings

    settings = get_settings()
    cache_dir = (
        settings.resolve_fastembed_cache_dir()
        if settings.embedding_provider.lower() == "local"
        else None
    )
    _cached_default = build_provider(
        settings.embedding_provider,
        settings.embedding_model or None,
        api_key=settings.gemini_api_key,
        cache_dir=cache_dir,
    )
    return _cached_default


def reset_default_provider() -> None:
    """Drop the cached default provider (used by tests)."""
    global _cached_default
    _cached_default = None
