import logging
from typing import Literal

from dblp_kgqa.modules.info_extractor.base import (
    BaseInfoExtractor,
    BaseInfoExtractorConfig,
)
from dblp_kgqa.modules.schemas import ExtractedInfo, PipelineOutput
from dblp_kgqa.services.dblp_quad import DblpQuadService, DblpQuadSplitType

logger = logging.getLogger(__name__)


class GoldInfoExtractorConfig(BaseInfoExtractorConfig):
    strategy: Literal["GoldInfoExtractor"] = "GoldInfoExtractor"
    dblp_quad_service_name: str = "dblp_quad"
    dblp_quad_split_type: DblpQuadSplitType = "test"


class GoldInfoExtractor(BaseInfoExtractor):
    def __init__(
        self,
        config: GoldInfoExtractorConfig,
        dblp_quad_service: DblpQuadService,
    ):
        self.config = config
        dataset = dblp_quad_service.load(
            split=config.dblp_quad_split_type,
            kind="questions",
        )

        self._index: dict[str, str] = {
            sample.question.string: sample.query_type
            for sample in dataset.questions
        }

    def __call__(self, pipeline_output: PipelineOutput) -> ExtractedInfo:
        question = pipeline_output.question
        gold_query_type = self._index.get(question)

        if gold_query_type is None:
            logger.warning(
                f"!!!! Gold entities not found for question: {question}"
            )
            return ExtractedInfo()

        result = ExtractedInfo(query_type=gold_query_type)
        logger.info(f"Done - Gold extracted info: {result.model_dump_json()}")
        return result