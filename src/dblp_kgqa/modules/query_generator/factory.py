from typing import Annotated

from pydantic import Field

from dblp_kgqa.modules.query_generator.base import (
    BaseQueryGenerator,
)
from dblp_kgqa.modules.query_generator.llm import (
    LLMQueryGenerator,
    LLMQueryGeneratorConfig,
)
from dblp_kgqa.modules.query_generator.llm_rag import (
    LLMRAGQueryGenerator,
    LLMRAGQueryGeneratorConfig,
)
from dblp_kgqa.modules.query_generator.mock import (
    MockQueryGenerator,
    MockQueryGeneratorConfig,
)
from dblp_kgqa.services.embedding import EmbeddingService
from dblp_kgqa.services.llm import LLMService
from dblp_kgqa.services.neo4j import Neo4jService
from dblp_kgqa.services.registry import ServiceRegistry

type QueryGeneratorConfig = Annotated[
    MockQueryGeneratorConfig
    | LLMQueryGeneratorConfig
    | LLMRAGQueryGeneratorConfig,
    Field(discriminator="strategy"),
]


class QueryGeneratorFactory:
    @staticmethod
    def create(
        config: QueryGeneratorConfig, service_registry: ServiceRegistry
    ) -> BaseQueryGenerator:
        if isinstance(config, LLMRAGQueryGeneratorConfig):
            llm_service = service_registry.get(
                config.llm_service_name, LLMService
            )
            embedding_service = service_registry.get(
                config.embedding_service_name, EmbeddingService
            )
            neo4j_service = service_registry.get(
                config.neo4j_service_name, Neo4jService
            )
            return LLMRAGQueryGenerator(
                config, llm_service, embedding_service, neo4j_service
            )
        if isinstance(config, LLMQueryGeneratorConfig):
            llm_service = service_registry.get(
                config.llm_service_name, expected_type=LLMService
            )
            return LLMQueryGenerator(config, llm_service)
        if isinstance(config, MockQueryGeneratorConfig):
            return MockQueryGenerator(config)