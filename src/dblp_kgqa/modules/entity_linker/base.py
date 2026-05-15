from abc import ABC, abstractmethod

from pydantic import BaseModel

from dblp_kgqa.modules.schemas import LinkedEntities, PipelineOutput


class BaseEntityLinkerConfig(BaseModel):
    pass


class BaseEntityLinker(ABC):
    @abstractmethod
    def __call__(self, pipeline_output: PipelineOutput) -> LinkedEntities:
        pass
