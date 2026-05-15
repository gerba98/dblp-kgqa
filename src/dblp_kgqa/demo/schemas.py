from pydantic import BaseModel, Field

from dblp_kgqa.pipeline.pipeline import PipelineConfig


class DemoConfig(BaseModel):
    pipeline_config: PipelineConfig = Field(default_factory=PipelineConfig)
