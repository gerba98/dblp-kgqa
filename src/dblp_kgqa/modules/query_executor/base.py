from abc import ABC, abstractmethod

from pydantic import BaseModel

from dblp_kgqa.modules.schemas import PipelineOutput, SparqlResult


class BaseQueryExecutorConfig(BaseModel):
    pass


class BaseQueryExecutor(ABC):
    @abstractmethod
    def __call__(self, pipeline_output: PipelineOutput) -> SparqlResult | None:
        pass
