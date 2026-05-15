from typing import Annotated

from pydantic import Field

from dblp_kgqa.services.base import BaseService
from dblp_kgqa.services.dblp_quad import DblpQuadService, DblpQuadServiceConfig
from dblp_kgqa.services.embedding import (
    EmbeddingService,
    EmbeddingServiceConfig,
)
from dblp_kgqa.services.llm import LLMService, LLMServiceConfig
from dblp_kgqa.services.neo4j import Neo4jService, Neo4jServiceConfig

type ServiceConfig = Annotated[
    LLMServiceConfig
    | Neo4jServiceConfig
    | DblpQuadServiceConfig
    | EmbeddingServiceConfig,
    Field(discriminator="type"),
]

class ServiceFactory:
    @staticmethod
    def create(config: ServiceConfig) -> BaseService:
        if isinstance(config, LLMServiceConfig):
            return LLMService(config)

        if isinstance(config, Neo4jServiceConfig):
            return Neo4jService(config)

        if isinstance(config, DblpQuadServiceConfig):
            return DblpQuadService(config)

        if isinstance(config, EmbeddingServiceConfig):
            return EmbeddingService(config)
