from abc import ABC, abstractmethod

from pydantic import BaseModel

from dblp_kgqa.modules.schemas import (
    GeneratedQuery,
    PipelineOutput,
)


class BaseQueryGeneratorConfig(BaseModel):
    pass


class BaseQueryGenerator(ABC):
    @abstractmethod
    def __call__(self, pipeline_output: PipelineOutput) -> GeneratedQuery:
        pass
