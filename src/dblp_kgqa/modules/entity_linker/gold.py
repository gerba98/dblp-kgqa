import logging
from typing import Literal

from dblp_kgqa.modules.entity_linker.base import (
    BaseEntityLinker,
    BaseEntityLinkerConfig,
)
from dblp_kgqa.modules.schemas import (
    LinkedEntities,
    LinkedEntity,
    PipelineOutput,
)
from dblp_kgqa.services.dblp_quad import (
    DblpQuadService,
    DblpQuadSplitType,
)

logger = logging.getLogger(__name__)

ENTITIES_PROMPT_CONTEXT = (
    "The 'entities' field in the user message lists entities linked from "
    "the question, each with a type (person/publication/venue) and a URI "
    "(possibly empty). Use these URIs verbatim in your SPARQL. Venue "
    "handling is governed by RULE 4."
)


class GoldEntityLinkerConfig(BaseEntityLinkerConfig):
    strategy: Literal["GoldEntityLinker"] = "GoldEntityLinker"
    dblp_quad_service_name: str = "dblp_quad"
    dblp_quad_split_type: DblpQuadSplitType = "test"


class GoldEntityLinker(BaseEntityLinker):
    def __init__(
        self,
        config: GoldEntityLinkerConfig,
        dblp_quad_service: DblpQuadService,
    ):
        self.config = config
        dataset = dblp_quad_service.load(
            split=config.dblp_quad_split_type,
            kind="questions",
        )

        self._index: dict[str, list[str]] = {
            sample.question.string: sample.entities
            for sample in dataset.questions
        }

    def __call__(self, pipeline_output: PipelineOutput) -> LinkedEntities:
        question = pipeline_output.question
        gold_entities = self._index.get(question)

        if gold_entities is None:
            logger.warning(
                f"!!!! Gold entities not found for question: {question}"
            )
            return LinkedEntities(description=ENTITIES_PROMPT_CONTEXT)

        result = LinkedEntities(description=ENTITIES_PROMPT_CONTEXT)
        for raw_entity in gold_entities:
            entity_type = self._infer_entity_type(raw_entity)
            if entity_type == "venue":
                result.linked_entities.append(
                    LinkedEntity(name=raw_entity, uri="", type="venue")
                )
            else:
                result.linked_entities.append(
                    LinkedEntity(
                        name="",
                        uri=raw_entity,
                        type=entity_type,
                    )
                )

        logger.info(f"Done - Gold linked entities: {result.model_dump_json()}")
        return result

    @staticmethod
    def _infer_entity_type(raw_entity: str) -> str:
        if "/pid/" in raw_entity:
            return "person"
        if "/rec/" in raw_entity:
            return "publication"
        return "venue"