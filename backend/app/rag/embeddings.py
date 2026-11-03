"""Turning text into vectors, so book passages can be found by meaning.

Business code depends on `EmbeddingProvider`. The adapter today runs the multilingual model
intfloat/multilingual-e5-base on this computer through ONNX (no PyTorch, no API key): English,
Hindi and Hinglish questions land near the right passages. It is downloaded (~1 GB) into
MODEL_CACHE_DIR the first time it is needed and then kept in memory.

A different model changes the vector size and meaning: it needs a migration (the column size)
and `python -m scripts.reembed`. Every stored vector records the model that made it.
"""

import asyncio
import logging
import time
from collections.abc import Sequence
from functools import lru_cache
from typing import Protocol

from app.core.config import get_settings
from app.models.library import EMBEDDING_DIMENSION

logger = logging.getLogger(__name__)


class EmbeddingProvider(Protocol):
    model_name: str
    # Below this cosine similarity the best passage is not about the question. It depends on the
    # model: multilingual-e5 scores cluster high (unrelated text still scores ~0.72).
    min_similarity: float

    async def embed_passages(self, texts: Sequence[str]) -> list[list[float]]: ...

    async def embed_query(self, text: str) -> list[float]: ...


class MultilingualE5Embeddings:
    """intfloat/multilingual-e5-base (MIT licence, 768 dimensions, reads up to 512 tokens).

    E5 models expect "passage: " in front of stored text and "query: " in front of questions.
    """

    model_name = "intfloat/multilingual-e5-base"
    min_similarity = 0.76  # tuned with `python -m scripts.eval_retrieval`
    _BATCH = 16

    def __init__(self, cache_dir: str) -> None:
        self._cache_dir = cache_dir
        self._model = None
        self._loading = asyncio.Lock()

    def _load(self):  # fastembed is imported lazily: it is large and only needed here
        from fastembed import TextEmbedding
        from fastembed.common.model_description import ModelSource, PoolingType

        if self.model_name not in {m["model"] for m in TextEmbedding.list_supported_models()}:
            TextEmbedding.add_custom_model(
                model=self.model_name,
                pooling=PoolingType.MEAN,
                normalization=True,
                sources=ModelSource(hf=self.model_name),
                dim=EMBEDDING_DIMENSION,
                model_file="onnx/model.onnx",
            )
        started = time.perf_counter()
        model = TextEmbedding(self.model_name, cache_dir=self._cache_dir)
        logger.info("Search model loaded in %.1f s", time.perf_counter() - started)
        return model

    async def _embed(self, texts: list[str]) -> list[list[float]]:
        async with self._loading:
            if self._model is None:
                self._model = await asyncio.to_thread(self._load)
        model = self._model
        vectors = await asyncio.to_thread(lambda: list(model.embed(texts, batch_size=self._BATCH)))
        return [vector.tolist() for vector in vectors]

    async def embed_passages(self, texts: Sequence[str]) -> list[list[float]]:
        return await self._embed([f"passage: {text}" for text in texts])

    async def embed_query(self, text: str) -> list[float]:
        return (await self._embed([f"query: {text}"]))[0]


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    return MultilingualE5Embeddings(str(get_settings().model_cache_path))
