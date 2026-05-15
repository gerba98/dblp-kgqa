from typing import Annotated

from pydantic import Field

from dblp_kgqa.modules.info_extractor.base import (
    BaseInfoExtractor,
)
from dblp_kgqa.modules.info_extractor.llm import (
    LLMInfoExtractor,
    LLMInfoExtractorConfig,
)
from dblp_kgqa.modules.info_extractor.mock import (
    MockInfoExtractor,
    MockInfoExtractorConfig,
)
from dblp_kgqa.services.llm import LLMService
from dblp_kgqa.services.registry import ServiceRegistry
from dblp_kgqa.modules.info_extractor.gold import (
    GoldInfoExtractor,
    GoldInfoExtractorConfig,
)
from dblp_kgqa.services.dblp_quad import DblpQuadService

type InfoExtractorConfig = Annotated[
    MockInfoExtractorConfig | LLMInfoExtractorConfig | GoldInfoExtractorConfig,
    Field(discriminator="strategy"),
]


class InfoExtractorFactory:
    @staticmethod
    def create(
        config: InfoExtractorConfig, service_registry: ServiceRegistry
    ) -> BaseInfoExtractor:
        if isinstance(config, LLMInfoExtractorConfig):
            llm_service = service_registry.get(
                config.llm_service_name, expected_type=LLMService
            )
            return LLMInfoExtractor(config, llm_service)

        if isinstance(config, GoldInfoExtractorConfig):
            dblp_quad_service = service_registry.get(
                config.dblp_quad_service_name, expected_type=DblpQuadService
            )
            return GoldInfoExtractor(config, dblp_quad_service)

        if isinstance(config, MockInfoExtractorConfig):
            return MockInfoExtractor(config)
