from typing import Literal

from dblp_kgqa.modules.query_generator.base import (
    BaseQueryGenerator,
    BaseQueryGeneratorConfig,
)
from dblp_kgqa.modules.schemas import (
    GeneratedQuery,
    PipelineOutput,
)


class MockQueryGeneratorConfig(BaseQueryGeneratorConfig):
    strategy: Literal["MockQueryGenerator"] = "MockQueryGenerator"


class MockQueryGenerator(BaseQueryGenerator):
    def __init__(
        self,
        config: MockQueryGeneratorConfig,
    ):
        self.config = config

    def __call__(self, pipeline_output: PipelineOutput) -> GeneratedQuery:

        return GeneratedQuery()
