from typing import Annotated

from pydantic import Field

from dblp_kgqa.modules.relation_linker.base import BaseRelationLinker
from dblp_kgqa.modules.relation_linker.full import (
    FullSchemaRelationLinker,
    FullSchemaRelationLinkerConfig,
)
from dblp_kgqa.modules.relation_linker.rag import (
    RAGRelationLinker,
    RAGRelationLinkerConfig,
)
from dblp_kgqa.services.embedding import EmbeddingService
from dblp_kgqa.services.neo4j import Neo4jService
from dblp_kgqa.services.registry import ServiceRegistry

type RelationLinkerConfig = Annotated[
    FullSchemaRelationLinkerConfig | RAGRelationLinkerConfig,
    Field(discriminator="strategy"),
]


class RelationLinkerFactory:
    @staticmethod
    def create(
        config: RelationLinkerConfig, service_registry: ServiceRegistry
    ) -> BaseRelationLinker:

        if isinstance(config, FullSchemaRelationLinkerConfig):
            return FullSchemaRelationLinker(config)
        if isinstance(config, RAGRelationLinkerConfig):
            neo4j_service = service_registry.get(
                config.neo4j_service_name, expected_type=Neo4jService
            )
            embedding_service = service_registry.get(
                config.embedding_service_name,
                expected_type=EmbeddingService,
            )
            return RAGRelationLinker(config, neo4j_service, embedding_service)
