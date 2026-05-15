from abc import ABC, abstractmethod

from pydantic import BaseModel

from dblp_kgqa.modules.schemas import (
    LinkedRelation,
    PipelineOutput,
)


class BaseRelationLinkerConfig(BaseModel):
    pass


class BaseRelationLinker(ABC):
    @abstractmethod
    def __call__(self, pipeline_output: PipelineOutput) -> LinkedRelation:
        pass