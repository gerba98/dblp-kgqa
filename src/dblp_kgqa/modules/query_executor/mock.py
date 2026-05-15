from typing import Literal

from dblp_kgqa.modules.query_executor.base import (
    BaseQueryExecutor,
    BaseQueryExecutorConfig,
)
from dblp_kgqa.modules.schemas import (
    AskResult,
    HeadAsk,
    PipelineOutput,
    SparqlResult,
)


class MockQueryExecutorConfig(BaseQueryExecutorConfig):
    strategy: Literal["MockQueryExecutor"] = "MockQueryExecutor"


class MockQueryExecutor(BaseQueryExecutor):
    def __init__(self, config: MockQueryExecutorConfig):
        self.config = config

    def __call__(self, pipeline_output: PipelineOutput) -> SparqlResult:

         return SparqlResult(AskResult(head=HeadAsk(), boolean=False))
