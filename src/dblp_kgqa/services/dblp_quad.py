import re
from typing import Literal, overload

from pydantic import BaseModel

from dblp_kgqa import PROJECT_ROOT
from dblp_kgqa.modules.schemas import SparqlResult
from dblp_kgqa.services.base import BaseService, BaseServiceConfig

DATA_DIR = PROJECT_ROOT / "data" / "dblp_quad"

# SCHEMAS ---------------------------------------------------------------------

# DBLP QuAD Questions
class Question(BaseModel):
    string: str


class SparqlQuery(BaseModel):
    sparql: str


QUERY_TYPE = Literal[
    "SINGLE_FACT",
    "MULTI_FACT",
    "DOUBLE_INTENT",
    "BOOLEAN",
    "NEGATION",
    "DOUBLE_NEGATION",
    "UNION",
    "DISAMBIGUATION",
    "COUNT",
    "SUPERLATIVE+COMPARATIVE",
]


class QuestionSample(BaseModel):
    id: str
    query_type: QUERY_TYPE
    question: Question
    paraphrased_question: Question
    query: SparqlQuery
    template_id: str
    entities: list[str]
    relations: list[str]
    temporal: bool
    held_out: bool


class DblpQuadQuestions(BaseModel):
    questions: list[QuestionSample]


# DBLP QuAD Answers
class AnswerSample(BaseModel):
    id: str
    answer: SparqlResult


class DblpQuadAnswers(BaseModel):
    answers: list[AnswerSample]


# SERVICE ---------------------------------------------------------------------

DblpQuadSplitType = Literal["train", "valid", "test"]
DblpQuadDataType = Literal["questions", "answers"]

class DblpQuadServiceConfig(BaseServiceConfig):
    type: Literal["DblpQuad"] = "DblpQuad"


class DblpQuadService(BaseService):
    def __init__(self, config: DblpQuadServiceConfig):
        self.config = config
        self._cache: dict[str, DblpQuadQuestions | DblpQuadAnswers] = {}

        if not DATA_DIR.exists():
            raise FileNotFoundError(
                f"DBLP-QuAD data not found at {DATA_DIR}. "
                "Run 'make init-data' first."
            )

    @overload
    def load(
        self, split: DblpQuadSplitType, kind: Literal["questions"]
    ) -> DblpQuadQuestions:
        pass

    @overload
    def load(
        self, split: DblpQuadSplitType, kind: Literal["answers"]
    ) -> DblpQuadAnswers:
        pass

    def load(
        self, split: DblpQuadSplitType, kind: DblpQuadDataType
    ) -> DblpQuadQuestions | DblpQuadAnswers:
        cache_key = f"{split}_{kind}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        path = DATA_DIR / split / f"{kind}.json"

        raw_text = path.read_text(encoding="utf-8")

        # Fix double-escaped unicode from DBLP-QuAD dataset
        raw_text = re.sub(
            r"\\\\u([0-9a-fA-F]{4})",
            lambda m: chr(int(m.group(1), 16)),
            raw_text,
        )

        data_class = (
            DblpQuadQuestions if kind == "questions" else DblpQuadAnswers
        )
        data = data_class.model_validate_json(raw_text)

        self._cache[cache_key] = data
        return data

    def clear_cache(self):
        self._cache.clear()
