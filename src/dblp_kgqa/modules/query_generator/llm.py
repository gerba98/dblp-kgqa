import logging
from typing import Literal

from dblp_kgqa import SchemaVersion
from dblp_kgqa.modules.query_generator.base import (
    BaseQueryGenerator,
    BaseQueryGeneratorConfig,
)
from dblp_kgqa.modules.query_generator.llm_prompt import (
    FEW_SHOT_EXAMPLES,
    FULL_SYSTEM_PROMPT,
    VENUE_PREDICATE_EXAMPLES,
    VENUE_RULES,
    HumanPrompt,
    LLMGeneratedQuery,
    LLMGeneratedQueryExp,
)
from dblp_kgqa.modules.schemas import (
    GeneratedQuery,
    PipelineOutput,
)
from dblp_kgqa.services.llm import LLMService, PromptMessage

logger = logging.getLogger(__name__)


class LLMQueryGeneratorConfig(BaseQueryGeneratorConfig):
    strategy: Literal["LLMQueryGenerator"] = "LLMQueryGenerator"
    llm_service_name: str = "google_llm"
    schema_version: SchemaVersion = "current"
    include_static_few_shot: bool = True
    include_explanation: bool = True
    format_yaml: bool = False


class LLMQueryGenerator(BaseQueryGenerator):
    def __init__(
        self,
        config: LLMQueryGeneratorConfig,
        llm_service: LLMService,
    ):
        self.config = config
        self.llm_service = llm_service
        self.system_prompt = FULL_SYSTEM_PROMPT
        self.venue_predicate_example = VENUE_PREDICATE_EXAMPLES[
            config.schema_version
        ]
        self.venue_rule = VENUE_RULES[config.schema_version]
        self.few_shot_examples = FEW_SHOT_EXAMPLES
        self.extraction_schema = (
            LLMGeneratedQueryExp
            if config.include_explanation
            else LLMGeneratedQuery
        )

    def __call__(self, pipeline_output: PipelineOutput) -> GeneratedQuery:

        question = pipeline_output.question
        linked_entities = pipeline_output.linked_entities
        linked_relation = pipeline_output.linked_relation

        # system prompt
        system_prompt = PromptMessage(
            role="system",
            content=self.system_prompt.format(
                entities_description=linked_entities.description,
                relations_description=linked_relation.description,
                venue_predicate_example=self.venue_predicate_example,
                venue_rule=self.venue_rule,
            ),
        )
        messages = [system_prompt]

        # few shot examples
        messages = self._get_few_shot_examples(messages)

        # current human prompt
        human_prompt = HumanPrompt(
            question=question,
            entities=linked_entities,
            relations=linked_relation,
        )
        human_prompt = (
            human_prompt.to_yaml_str()
            if self.config.format_yaml
            else human_prompt.model_dump_json()
        )
        curr_human_prompt = PromptMessage(role="human", content=human_prompt)
        messages.append(curr_human_prompt)

        # query generation
        generated_query = self.llm_service.invoke_with_structured_output(
            prompt_messages=messages,
            output_schema=self.extraction_schema,
        )
        result = GeneratedQuery.model_validate(generated_query.model_dump())

        if isinstance(generated_query, LLMGeneratedQueryExp):
            logger.debug(
                ">>>> generated_query.explanation:"
                f"{generated_query.explanation}"
            )

        logger.info(f"DONE - Generated query: {result.model_dump_json()}")

        return result

    def _get_few_shot_examples(
        self, messages: list[PromptMessage]
    ) -> list[PromptMessage]:

        if not self.config.include_static_few_shot:
            return messages

        exclude_fields = (
            None if self.config.include_explanation else {"explanation"}
        )

        for example in self.few_shot_examples:
            human_prompt = (
                example.human_prompt.to_yaml_str()
                if self.config.format_yaml
                else example.human_prompt.model_dump_json()
            )
            human_example = PromptMessage(
                role="human",
                content=human_prompt,
            )
            messages.append(human_example)
            ai_response = example.ai_response.model_dump_json(
                exclude=exclude_fields
            )
            ai_example = PromptMessage(role="ai", content=ai_response)
            messages.append(ai_example)
        return messages
