import logging
from collections.abc import Iterator

from pydantic import BaseModel, Field

from dblp_kgqa.modules.entity_linker.api import ApiEntityLinkerConfig
from dblp_kgqa.modules.entity_linker.base import BaseEntityLinker
from dblp_kgqa.modules.entity_linker.factory import EntityLinkerConfig
from dblp_kgqa.modules.info_extractor.base import BaseInfoExtractor
from dblp_kgqa.modules.info_extractor.factory import InfoExtractorConfig
from dblp_kgqa.modules.info_extractor.llm import LLMInfoExtractorConfig
from dblp_kgqa.modules.query_executor.base import BaseQueryExecutor
from dblp_kgqa.modules.query_executor.endpoint import (
    EndpointQueryExecutorConfig,
)
from dblp_kgqa.modules.query_executor.factory import QueryExecutorConfig
from dblp_kgqa.modules.query_generator.base import BaseQueryGenerator
from dblp_kgqa.modules.query_generator.factory import QueryGeneratorConfig
from dblp_kgqa.modules.query_generator.llm_rag import (
    LLMRAGQueryGeneratorConfig,
)
from dblp_kgqa.modules.relation_linker.base import BaseRelationLinker
from dblp_kgqa.modules.relation_linker.factory import RelationLinkerConfig
from dblp_kgqa.modules.relation_linker.rag import RAGRelationLinkerConfig
from dblp_kgqa.modules.schemas import (
    ExtractedInfo,
    GeneratedQuery,
    LinkedEntities,
    LinkedRelation,
    PipelineOutput,
)

logger = logging.getLogger(__name__)


class PipelineConfig(BaseModel):
    info_extractor_config: InfoExtractorConfig = Field(
        default_factory=LLMInfoExtractorConfig
    )
    entity_linker_config: EntityLinkerConfig = Field(
        default_factory=ApiEntityLinkerConfig
    )
    relation_linker_config: RelationLinkerConfig = Field(
        default_factory=RAGRelationLinkerConfig
    )
    query_generator_config: QueryGeneratorConfig = Field(
        default_factory=LLMRAGQueryGeneratorConfig
    )
    query_executor_config: QueryExecutorConfig = Field(
        default_factory=EndpointQueryExecutorConfig
    )


class KGQAPipeline:
    def __init__(
        self,
        info_extractor: BaseInfoExtractor,
        entity_linker: BaseEntityLinker,
        relation_linker: BaseRelationLinker,
        query_generator: BaseQueryGenerator,
        query_executor: BaseQueryExecutor,
    ):
        self.info_extractor = info_extractor
        self.entity_linker = entity_linker
        self.relation_linker = relation_linker
        self.query_generator = query_generator
        self.query_executor = query_executor

    def run_iter(self, question: str) -> Iterator[tuple[str, PipelineOutput]]:
        state = PipelineOutput(
            question=question,
            extracted_info=ExtractedInfo(),
            linked_entities=LinkedEntities(),
            linked_relation=LinkedRelation(),
            generated_query=GeneratedQuery(),
        )
        logger.info(f"QUESTION: {question}")

        state.extracted_info = self.info_extractor(state)
        yield "info_extractor", state

        state.linked_entities = self.entity_linker(state)
        yield "entity_linker", state

        state.linked_relation = self.relation_linker(state)
        yield "relation_linker", state

        state.generated_query = self.query_generator(state)
        yield "query_generator", state

        state.sparql_result = self.query_executor(state)
        yield "query_executor", state

    def run(self, question: str) -> PipelineOutput:
        state = PipelineOutput(
            question=question,
            extracted_info=ExtractedInfo(),
            linked_entities=LinkedEntities(),
            linked_relation=LinkedRelation(),
            generated_query=GeneratedQuery(),
        )
        logger.info(f"QUESTION: {question}")
        state.extracted_info = self.info_extractor(state)
        state.linked_entities = self.entity_linker(state)
        state.linked_relation = self.relation_linker(state)
        state.generated_query = self.query_generator(state)
        state.sparql_result = self.query_executor(state)
        return state
