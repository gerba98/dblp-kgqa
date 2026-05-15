from abc import ABC, abstractmethod

from pydantic import BaseModel

from dblp_kgqa.modules.schemas import ExtractedInfo, PipelineOutput


class BaseInfoExtractorConfig(BaseModel):
    pass

class BaseInfoExtractor(ABC):
    @abstractmethod
    def __call__(self, pipeline_output: PipelineOutput) -> ExtractedInfo:
        pass
