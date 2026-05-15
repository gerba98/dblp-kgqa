from typing import Literal

from pydantic import BaseModel, Field, RootModel


# ENTITY INFO EXTRACTOR OUTPUT ------------------------------------------------
class NamedEntity(BaseModel):
    name: str
    type: Literal["person", "venue", "publication"]


class ExtractedInfo(BaseModel):
    query_type: str = ""
    named_entities: list[NamedEntity] = Field(default_factory=list)


# ENTITY LINKER OUTPUT --------------------------------------------------------
class LinkedEntity(BaseModel):
    name: str
    uri: str
    type: str


class LinkedEntities(BaseModel):
    description: str = Field(default="", exclude=True)
    linked_entities: list[LinkedEntity] = Field(default_factory=list)


# RELATION LINKER OUTPUT ------------------------------------------------------
class LinkedRelation(BaseModel):
    description: str = Field(default="", exclude=True)
    schema_context: list[str] = Field(default_factory=list)


# QUERY GENERATOR OUTPUT ------------------------------------------------------
class GeneratedQuery(BaseModel):
    query: str = ""


# Query executor output -------------------------------------------------------


# ASK Result
class HeadAsk(BaseModel):
    link: list[str] | None = None


class AskResult(BaseModel):
    head: HeadAsk
    boolean: bool


# SELECT Result


class HeadSelect(BaseModel):
    link: list[str] | None = None
    vars: list[str]


class UriBinding(BaseModel):
    type: Literal["uri"]
    value: str


class BNodeBinding(BaseModel):
    type: Literal["bnode"]
    value: str


class LiteralLangBinding(BaseModel):
    type: Literal["literal"]
    value: str
    xml_lang: str = Field(..., alias="xml:lang")


class LiteralDatatypeBinding(BaseModel):
    type: Literal["literal", "typed-literal"]  # "typed-literal" for DBLP QuAD
    value: str
    datatype: str | None = None


class SelectResults(BaseModel):
    distinct: bool | None = None
    ordered: bool | None = None
    bindings: list[
        dict[
            str,
            UriBinding
            | BNodeBinding
            | LiteralLangBinding
            | LiteralDatatypeBinding,
        ]
    ]


class SelectResult(BaseModel):
    head: HeadSelect
    results: SelectResults


# Result
class SparqlResult(RootModel[AskResult | SelectResult]):
    root: AskResult | SelectResult

# Pipeline output -------------------------------------------------------------

class PipelineOutput(BaseModel):
    question: str
    extracted_info: ExtractedInfo
    linked_entities: LinkedEntities
    linked_relation: LinkedRelation
    generated_query: GeneratedQuery
    sparql_result: SparqlResult | None = None  # populated by query_executor
