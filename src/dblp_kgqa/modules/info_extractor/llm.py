import logging
import unicodedata
from typing import Literal

from dblp_kgqa.modules.info_extractor.base import (
    BaseInfoExtractor,
    BaseInfoExtractorConfig,
)
from dblp_kgqa.modules.info_extractor.llm_prompt import (
    FEW_SHOT_EXAMPLES,
    SYSTEM_PROMPT,
    HumanPrompt,
    LLMExtractedInfo,
)
from dblp_kgqa.modules.schemas import ExtractedInfo, PipelineOutput
from dblp_kgqa.services.llm import LLMService, PromptMessage

logger = logging.getLogger(__name__)


class LLMInfoExtractorConfig(BaseInfoExtractorConfig):
    strategy: Literal["LLMInfoExtractor"] = "LLMInfoExtractor"
    llm_service_name: str = "google_llm"


class LLMInfoExtractor(BaseInfoExtractor):
    def __init__(
        self,
        config: LLMInfoExtractorConfig,
        llm_service: LLMService,
    ):
        self.config = config
        self.llm_service = llm_service
        self.system_prompt = SYSTEM_PROMPT
        self.few_shot_examples = FEW_SHOT_EXAMPLES
        self.extraction_schema = LLMExtractedInfo

    def __call__(self, pipeline_output: PipelineOutput) -> ExtractedInfo:
        question = unicodedata.normalize("NFC", pipeline_output.question)

        # system prompt
        system_prompt = PromptMessage(
            role="system", content=self.system_prompt
        )
        messages = [system_prompt]

        # few shot examples
        messages = self._get_few_shot_examples(messages)

        # current human prompt
        human_prompt = HumanPrompt(question=question)
        curr_human_prompt = PromptMessage(
            role="human", content=human_prompt.model_dump_json()
        )
        messages.append(curr_human_prompt)

        # extraction
        extracted_info = self.llm_service.invoke_with_structured_output(
            prompt_messages=messages,
            output_schema=self.extraction_schema,
        )
        result = ExtractedInfo.model_validate(extracted_info.model_dump())

        logger.debug(
            ">>>> extracted_info.explanation:"
            f"{extracted_info.explanation}"
        )
        logger.info(f"DONE - Extracted info: {result.model_dump_json()}")
        return result

    def _get_few_shot_examples(
        self, messages: list[PromptMessage]
    ) -> list[PromptMessage]:
        for example in self.few_shot_examples:
            human_example = PromptMessage(
                role="human",
                content=example.human_prompt.model_dump_json(),
            )
            messages.append(human_example)
            ai_example = PromptMessage(
                role="ai",
                content=example.ai_response.model_dump_json(),
            )
            messages.append(ai_example)
        return messages
