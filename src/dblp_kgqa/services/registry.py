from pydantic import BaseModel, Field

from dblp_kgqa.services.base import BaseService
from dblp_kgqa.services.dblp_quad import DblpQuadServiceConfig
from dblp_kgqa.services.embedding import EmbeddingServiceConfig
from dblp_kgqa.services.factory import ServiceConfig, ServiceFactory
from dblp_kgqa.services.llm import (
    GoogleBackendConfig,
    LlamaCppBackendConfig,
    LLMServiceConfig,
)
from dblp_kgqa.services.neo4j import Neo4jServiceConfig


class ServiceRegistryConfig(BaseModel):
    model_config = {"extra": "allow"}

    google_llm: ServiceConfig = Field(
        default_factory=lambda: LLMServiceConfig(
            backend=GoogleBackendConfig(),
        )
    )

    local_llm: ServiceConfig = Field(
        default_factory=lambda: LLMServiceConfig(
            backend=LlamaCppBackendConfig(),
        )
    )

    local_neo4j: ServiceConfig = Field(
        default_factory=lambda: Neo4jServiceConfig()
    )

    dblp_quad: ServiceConfig = Field(
        default_factory=lambda: DblpQuadServiceConfig()
    )

    google_embedding_ss: ServiceConfig = Field(
        default_factory=lambda: EmbeddingServiceConfig(
            task_type="SEMANTIC_SIMILARITY"
        )
    )

    google_embedding_rq: ServiceConfig = Field(
        default_factory=lambda: EmbeddingServiceConfig(
            task_type="RETRIEVAL_QUERY"
        )
    )



class ServiceRegistry:
    def __init__(self):
        self._services: dict[str, BaseService] = {}

    def load_services(self, config: ServiceRegistryConfig):
        for service_name, service_config in config:
            self.load_service(service_name, service_config)

    def load_service(self, name: str, config: ServiceConfig):
        if name in self._services:
            raise ValueError(f"Service '{name}' already registered.")
        self._services[name] = ServiceFactory.create(config)

    def get[T: BaseService](
        self,
        name: str,
        expected_type: type[T],
    ) -> T:
        try:
            service = self._services[name]
        except KeyError:
            raise KeyError(f"Undefined service '{name}'") from None

        if not isinstance(service, expected_type):
            raise TypeError(
                f"Service '{name}' is {type(service).__name__}, "
                f"expected {expected_type.__name__}"
            )

        return service
