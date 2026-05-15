import logging
from typing import Any, Literal

from pydantic import Field

from dblp_kgqa import SchemaVersion
from dblp_kgqa.modules.query_generator.llm import (
    LLMQueryGenerator,
    LLMQueryGeneratorConfig,
)
from dblp_kgqa.modules.query_generator.llm_prompt import (
    FewShotExample,
    HumanPrompt,
    LLMGeneratedQueryExp,
)
from dblp_kgqa.modules.schemas import (
    GeneratedQuery,
    LinkedEntities,
    LinkedEntity,
    LinkedRelation,
    PipelineOutput,
)
from dblp_kgqa.services.embedding import EmbeddingService
from dblp_kgqa.services.llm import LLMService, PromptMessage
from dblp_kgqa.services.neo4j import Neo4jService

logger = logging.getLogger(__name__)

# UTILS -----------------------------------------------------------------------
def _dblp_quad_paths(model_name: str) -> tuple[str, str, str]:
    model_slug = model_name.replace("/", "_")
    return (
        "data/dblp_quad/train/questions.json",
        f"data/dblp_quad/train/embeddings_{model_slug}.json",
        "data/dblp_quad/train/explanations.json",
    )

# MODULE ----------------------------------------------------------------------

class LLMRAGQueryGeneratorConfig(LLMQueryGeneratorConfig):
    strategy: Literal["LLMRAGQueryGenerator"] = "LLMRAGQueryGenerator"  # pyright: ignore[reportIncompatibleVariableOverride]
    llm_service_name: str = "google_llm"
    schema_version: SchemaVersion = "current"
    include_static_few_shot: bool = False
    include_explanation: bool = True
    format_yaml: bool = False
    # RAG
    embedding_service_name: str = "google_embedding_ss"
    neo4j_service_name: str = "local_neo4j"
    num_dynamic_few_shot: int = Field(default=5, ge=0)
    filter_by_query_type: bool = True

class LLMRAGQueryGenerator(LLMQueryGenerator):
    def __init__(
        self,
        config: LLMRAGQueryGeneratorConfig,
        llm_service: LLMService,
        embedding_service: EmbeddingService,
        neo4j_service: Neo4jService,
    ):
        super().__init__(config, llm_service)
        self.config = config

        self.embedding_service = embedding_service
        self.neo4j_service = neo4j_service
        if config.num_dynamic_few_shot > 0:
            questions_file, embeddings_file, explanations_file = (
                _dblp_quad_paths(embedding_service.config.model_name)
            )
            neo4j_service.load_dblp_quad(
                questions_file=questions_file,
                questions_embeddings_file=embeddings_file,
                explanations_file=explanations_file,
            )

    def __call__(self, pipeline_output: PipelineOutput) -> GeneratedQuery:
        self.last_question = pipeline_output.question
        self.last_query_type = pipeline_output.extracted_info.query_type
        return super().__call__(pipeline_output)

    def _get_few_shot_examples(
        self, messages: list[PromptMessage]
    ) -> list[PromptMessage]:

        # Static few-shot
        messages = super()._get_few_shot_examples(messages)

        # Dynamic few-shot
        if self.config.num_dynamic_few_shot == 0:
            return messages

        query_type = (
            self.last_query_type if self.config.filter_by_query_type else None
        )

        exclude_fields = (
            None if self.config.include_explanation else {"explanation"}
        )

        embedding = self.embedding_service.embed(self.last_question)
        results = self.neo4j_service.search_dblp_quad(
            embedding=embedding,
            query_type=query_type,
            k=self.config.num_dynamic_few_shot,
        )
        logger.debug(
            f">>>> {len(results)} RAG few-shot examples found from"
            f"{query_type if query_type is not None else 'ALL'} query type"
        )

        for result in results:
            r = result["result"]
            logger.debug(
                f">>>> RAG hit: id={r['id']} score={r['score']:.4f} "
                f"q={r['question']}"
            )
            example = self._build_few_shot_example(r)

            human_prompt = (
                example.human_prompt.to_yaml_str()
                if self.config.format_yaml
                else example.human_prompt.model_dump_json()
            )
            messages.append(PromptMessage(role="human", content=human_prompt))

            ai_response = example.ai_response.model_dump_json(
                exclude=exclude_fields
            )
            messages.append(PromptMessage(role="ai", content=ai_response))

        return messages

    @staticmethod
    def _build_few_shot_example(result: dict[str, Any]) -> FewShotExample:

        entities = LinkedEntities(
            linked_entities=[
                LinkedEntity(
                    name=uri
                    if __class__._infer_entity_type(uri) == "venue"
                    else "",
                    uri=""
                    if __class__._infer_entity_type(uri) == "venue"
                    else uri,
                    type=__class__._infer_entity_type(uri),
                )
                for uri in result["entities"]
            ]
        )
        relations = LinkedRelation(schema_context=result["relations"])

        human_prompt = HumanPrompt(
            question=result["question"],
            entities=entities,
            relations=relations,
        )
        ai_response = LLMGeneratedQueryExp(
            explanation=result["explanation"],
            query=result["sparql"],
        )
        return FewShotExample(
            human_prompt=human_prompt,
            ai_response=ai_response,
        )

    @staticmethod
    def _infer_entity_type(uri: str) -> str:
        if "/pid/" in uri:
            return "person"
        if "/rec/" in uri:
            return "publication"
        return "venue"