from typing import Annotated

from pydantic import Field

from dblp_kgqa.modules.entity_linker.api import (
    ApiEntityLinker,
    ApiEntityLinkerConfig,
)
from dblp_kgqa.modules.entity_linker.base import BaseEntityLinker
from dblp_kgqa.modules.entity_linker.gold import (
    GoldEntityLinker,
    GoldEntityLinkerConfig,
)
from dblp_kgqa.modules.entity_linker.mock import (
    MockEntityLinker,
    MockEntityLinkerConfig,
)
from dblp_kgqa.services.dblp_quad import DblpQuadService
from dblp_kgqa.services.registry import ServiceRegistry

type EntityLinkerConfig = Annotated[
    MockEntityLinkerConfig | ApiEntityLinkerConfig | GoldEntityLinkerConfig,
    Field(discriminator="strategy"),
]


class EntityLinkerFactory:
    @staticmethod
    def create(
        config: EntityLinkerConfig, service_registry: ServiceRegistry
    ) -> BaseEntityLinker:
        if isinstance(config, MockEntityLinkerConfig):
            return MockEntityLinker(config)
        if isinstance(config, ApiEntityLinkerConfig):
            return ApiEntityLinker(config)
        if isinstance(config, GoldEntityLinkerConfig):
            dblp_quad_service = service_registry.get(
                config.dblp_quad_service_name, expected_type=DblpQuadService
            )
            return GoldEntityLinker(config, dblp_quad_service)
