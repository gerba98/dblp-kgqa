import json
import logging
from typing import Literal

from dblp_kgqa.modules.relation_linker.base import (
    BaseRelationLinker,
    BaseRelationLinkerConfig,
)
from dblp_kgqa.modules.relation_linker.full_schema import (
    PROPERTIES_URI_AND_DESCRIPTION,
)
from dblp_kgqa.modules.schemas import (
    LinkedRelation,
    PipelineOutput,
)

logger = logging.getLogger(__name__)

RELATIONS_PROMPT_CONTEXT = (
    "The 'relations' field in the user message lists the DBLP schema "
    "predicate URIs, mapping each property name to its official 'IRI' and "
    "a natural-language 'description'. Read descriptions carefully. Use "
    "ONLY these predicates in your triple patterns. Never invent predicates."
)


class FullSchemaRelationLinkerConfig(BaseRelationLinkerConfig):
    strategy: Literal["FullSchemaRelationLinker"] = "FullSchemaRelationLinker"


class FullSchemaRelationLinker(BaseRelationLinker):
    def __init__(self, config: FullSchemaRelationLinkerConfig):
        self.config = config
        raw_schema = PROPERTIES_URI_AND_DESCRIPTION
        self.full_schema = json.dumps(raw_schema, indent=4)

    def __call__(self, pipeline_output: PipelineOutput) -> LinkedRelation:

        logger.info("DONE - Linked relation: <FULL_SCHEMA_OMITTED_HERE>")

        return LinkedRelation(
            description=RELATIONS_PROMPT_CONTEXT,
            schema_context=[self.full_schema],
        )
