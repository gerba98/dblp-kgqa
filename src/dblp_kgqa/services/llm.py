import logging
from typing import Annotated, Any, Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, SecretStr

from dblp_kgqa import settings
from dblp_kgqa.services.base import BaseService, BaseServiceConfig

logger = logging.getLogger(__name__)


class PromptMessage(BaseModel):
    role: Literal["system", "human", "ai"]
    content: str


GoogleModels = Literal[
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite-preview",
]

LlamaCppModels= Literal[
    "Qwen3.5-4B-UD-Q4_K_XL",
    "Qwen3.5-2B-UD-Q5_K_XL"
]

class GoogleBackendConfig(BaseModel):
    strategy: Literal["Google"] = "Google"
    model_name: GoogleModels = "gemini-3.1-flash-lite-preview"
    thinking_level: Literal["minimal", "low", "medium", "high"] = "minimal"
    use_vertexai: bool = False

# Unsloth recommended parameters for qwen3.5-small
# https://unsloth.ai/docs/models/qwen3.5#qwen3.5-small-0.8b-2b-4b-9b
class LlamaCppBackendConfig(BaseModel):
    strategy: Literal["LlamaCpp"] = "LlamaCpp"
    model_name: LlamaCppModels = "Qwen3.5-4B-UD-Q4_K_XL"
    base_url: str = "http://llama-server:8080"
    ctx_size: int = 16384
    n_gpu_layers: int = 99
    top_p: float | None = 0.8
    top_k: int | None = 20
    min_p: float | None = 0.0
    presence_penalty: float | None = 1.5
    enable_thinking: bool = False


class LLMServiceConfig(BaseServiceConfig):
    type: Literal["LLM"] = "LLM"
    temperature: float = 0.0
    max_retries: int = 3
    max_tokens: int | None = 2048
    backend: Annotated[
        GoogleBackendConfig | LlamaCppBackendConfig,
        Field(discriminator="strategy"),
    ]


class LLMService(BaseService):
    def __init__(self, config: LLMServiceConfig):
        self.config = config
        self._model = self._create_model()

    def _create_model(self) -> BaseChatModel:
        config_backend = self.config.backend

        if isinstance(config_backend, GoogleBackendConfig):
            kwargs: dict[str, Any] = dict(
                model=config_backend.model_name,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                thinking_level=config_backend.thinking_level,
                timeout=300,
            )
            if config_backend.use_vertexai:
                kwargs.update(
                    vertexai=True,
                    project=settings.google_cloud_project,
                    location=settings.google_cloud_location,
                )
            else:
                kwargs["google_api_key"] = settings.google_api_key
            return ChatGoogleGenerativeAI(**kwargs)

        elif isinstance(config_backend, LlamaCppBackendConfig):
            # top_k and min_p are llama.cpp-specific (not in OpenAI API).
            extra_body: dict[str, Any] = {
                "chat_template_kwargs": {
                    "enable_thinking": config_backend.enable_thinking
                }
            }
            if config_backend.top_k is not None:
                extra_body["top_k"] = config_backend.top_k
            if config_backend.min_p is not None:
                extra_body["min_p"] = config_backend.min_p

            return ChatOpenAI(
                model=config_backend.model_name,
                base_url=f"{config_backend.base_url.rstrip('/')}/v1",
                api_key=SecretStr("not-needed"),
                temperature=self.config.temperature,
                max_completion_tokens=self.config.max_tokens,
                top_p=config_backend.top_p,
                presence_penalty=config_backend.presence_penalty,
                extra_body=extra_body or None,
            )

        raise ValueError(f"Backend LLM non supportato: {type(config_backend)}")

    def _build_messages(
        self, prompt_messages: list[PromptMessage]
    ) -> list[SystemMessage | HumanMessage | AIMessage]:
        mapping = {
            "system": SystemMessage,
            "human": HumanMessage,
            "ai": AIMessage,
        }
        return [
            mapping[msg.role](content=msg.content) for msg in prompt_messages
        ]

    def invoke_with_structured_output[T: BaseModel](
        self, prompt_messages: list[PromptMessage], output_schema: type[T]
    ) -> T:

        messages = self._build_messages(prompt_messages)
        structured_llm = self._model.with_structured_output(output_schema)

        last_exception = None
        max_retries = self.config.max_retries
        for attempt in range(max_retries):
            if attempt > 0:
                original_content = messages[-1].content
                if isinstance(original_content, str):
                    messages[-1].content = original_content + " "

            try:
                result = structured_llm.invoke(messages)
                return output_schema.model_validate(result)
            except Exception as e:
                logger.warning(
                    f"!!!! Attempt {attempt + 1}/{max_retries} failed.\n"
                    f"Error: {type(e).__name__} - {str(e)}"
                )

                last_exception = e

        raise RuntimeError(
            f"LLM generation failed after {max_retries} attempts."
        ) from last_exception

    def raw_model(self) -> BaseChatModel:
        return self._model
