from typing import Literal

from dblp_kgqa.modules.entity_linker.base import (
    BaseEntityLinker,
    BaseEntityLinkerConfig,
)
from dblp_kgqa.modules.schemas import (
    LinkedEntities,
    PipelineOutput,
)


class MockEntityLinkerConfig(BaseEntityLinkerConfig):
    strategy: Literal["MockEntityLinker"] = "MockEntityLinker"


class MockEntityLinker(BaseEntityLinker):
    def __init__(self, config: MockEntityLinkerConfig):
        self.config = config

    def __call__(self, pipeline_output: PipelineOutput) -> LinkedEntities:

        return LinkedEntities()
