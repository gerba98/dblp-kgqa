from typing import Annotated

from pydantic import Field

from dblp_kgqa.modules.query_executor.base import BaseQueryExecutor
from dblp_kgqa.modules.query_executor.endpoint import (
    EndpointQueryExecutor,
    EndpointQueryExecutorConfig,
)
from dblp_kgqa.modules.query_executor.mock import (
    MockQueryExecutor,
    MockQueryExecutorConfig,
)
from dblp_kgqa.services.registry import ServiceRegistry

type QueryExecutorConfig = Annotated[
    MockQueryExecutorConfig | EndpointQueryExecutorConfig,
    Field(discriminator="strategy"),
]


class QueryExecutorFactory:
    @staticmethod
    def create(
        config: QueryExecutorConfig, service_registry: ServiceRegistry
    ) -> BaseQueryExecutor:
        if isinstance(config, EndpointQueryExecutorConfig):
            return EndpointQueryExecutor(config)
        if isinstance(config, MockQueryExecutorConfig):
            return MockQueryExecutor(config)
