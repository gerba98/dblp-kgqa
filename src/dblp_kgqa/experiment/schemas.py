from pydantic import BaseModel, Field

from dblp_kgqa.modules.schemas import PipelineOutput
from dblp_kgqa.pipeline.pipeline import PipelineConfig
from dblp_kgqa.services.dblp_quad import DblpQuadSplitType


class ExpConfig(BaseModel):
    exp_description: str = "---"
    split: DblpQuadSplitType = "test"
    pipeline_config: PipelineConfig = Field(default_factory=PipelineConfig)


class ExpResult(BaseModel):
    id: str
    result: PipelineOutput


class ExpResults(BaseModel):
    exp_results: list[ExpResult] = Field(default_factory=list)
