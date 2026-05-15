import logging
from typing import Literal

from dblp_kgqa.modules.info_extractor.base import (
    BaseInfoExtractor,
    BaseInfoExtractorConfig,
)
from dblp_kgqa.modules.schemas import ExtractedInfo, PipelineOutput

logger = logging.getLogger(__name__)

class MockInfoExtractorConfig(BaseInfoExtractorConfig):
    strategy: Literal["MockInfoExtractor"] = "MockInfoExtractor"


class MockInfoExtractor(BaseInfoExtractor):
    def __init__(self, config: MockInfoExtractorConfig):
        self.config = config

    def __call__(self, pipeline_output: PipelineOutput) -> ExtractedInfo:
        logger.debug("Mock Info Extractor")
        return ExtractedInfo()
