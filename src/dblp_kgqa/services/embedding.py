import logging
from typing import Any, Literal

from langchain_core.embeddings import Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from dblp_kgqa import settings
from dblp_kgqa.services.base import BaseService, BaseServiceConfig

logger = logging.getLogger(__name__)


GoogleEmbeddingModels = Literal[
    "gemini-embedding-001",
]

GoogleEmbeddingTaskType = Literal[
    "RETRIEVAL_QUERY",
    "RETRIEVAL_DOCUMENT",
    "SEMANTIC_SIMILARITY",
    "CLASSIFICATION",
    "CLUSTERING",
    "QUESTION_ANSWERING",
    "FACT_VERIFICATION",
    "CODE_RETRIEVAL_QUERY",
]


class EmbeddingServiceConfig(BaseServiceConfig):
    type: Literal["Embedding"] = "Embedding"
    model_name: GoogleEmbeddingModels = "gemini-embedding-001"
    task_type: GoogleEmbeddingTaskType = "SEMANTIC_SIMILARITY"
    use_vertexai: bool = False


class EmbeddingService(BaseService):
    def __init__(self, config: EmbeddingServiceConfig):
        self.config = config
        self._model = self._create_model()

    def _create_model(self) -> Embeddings:
        kwargs: dict[str, Any] = dict(
            model=self.config.model_name,
            task_type=self.config.task_type,
        )
        if self.config.use_vertexai:
            kwargs.update(
                vertexai=True,
                project=settings.google_cloud_project,
                # location=settings.google_cloud_location,
                location="europe-west8"
            )
        else:
            kwargs["google_api_key"] = settings.google_api_key
        return GoogleGenerativeAIEmbeddings(**kwargs)  # type: ignore[call-arg]

    def raw_model(self) -> Embeddings:
        return self._model

    def embed(self, text: str) -> list[float]:
        return self._model.embed_query(text)
    

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return self._model.embed_documents(texts)
