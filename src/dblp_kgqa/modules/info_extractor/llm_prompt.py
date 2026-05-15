# ruff: noqa: E501

from typing import Literal

from pydantic import BaseModel, Field

from dblp_kgqa.services.dblp_quad import QUERY_TYPE

# SYSTEM PROMPT ---------------------------------------------------------------

SYSTEM_PROMPT = """You are an information extractor for a KGQA system over the DBLP bibliographic database. From the user's question, extract `named_entities` and the `query_type`.

### Entity rules
- **person**: author or researcher names.
- **venue**: conference or journal names ONLY. Institutions and universities (e.g. 'MIT', 'ETH Zürich') are NOT venues — do not extract them at all.
- **publication**: exact paper or book titles ONLY. Topic descriptions (e.g. 'paper on neural networks') are NOT publications — do not extract them.
- Extract every distinct person, venue, and publication mentioned in the question.

### Query type cues
- Yes/no questions: no 'not' → BOOLEAN; a single 'not' → NEGATION; consecutive 'not not' → DOUBLE_NEGATION.
- Counting requests ('how many', 'count of', 'number of') → COUNT.
- Superlative or comparative phrases ('first', 'last', 'most', 'highest', 'lowest', 'more than', 'fewer than') → SUPERLATIVE+COMPARATIVE.
- Two related answers requested per result (e.g. papers AND year) → DOUBLE_INTENT.
- Two alternative branches over the same variable (e.g. venue A or venue B) → UNION.
- A topic descriptive phrase used as a constraint ('about X', 'on Y', 'related to Z') → DISAMBIGUATION (takes precedence over MULTI_FACT).
- Multiple direct constraints on the answer, or chaining through an intermediate variable → MULTI_FACT; a single direct fact about one entity → SINGLE_FACT.
"""


# STRUCTURED OUTPUT -----------------------------------------------------------

class LLMNamedEntity(BaseModel):
    name: str = Field(
        description=(
            "The exact textual span representing the entity name "
            "(e.g., 'Wazir Muhammad', 'MMAR', 'Attention is All You Need')."
        ),
    )
    type: Literal["person", "venue", "publication"] = Field(
        description=(
            "The category of the named entity: 'person', 'venue', or 'publication'. "
            "Routes the Entity Linking step to the correct DBLP API endpoint."
        ),
    )


class LLMExtractedInfo(BaseModel):
    explanation: str = Field(
        max_length=1200,
        description=(
            "Step-by-step reasoning before extraction: identify what the user is "
            "asking for, list the named entities and their types, and justify the "
            "chosen query_type by pointing to specific surface cues."
        ),
    )
    named_entities: list[LLMNamedEntity] = Field(
        default_factory=list,
        description=(
            "List of named entities (persons, venues, publications) to be resolved "
            "via the DBLP Entity Linking API."
        ),
    )
    query_type: QUERY_TYPE = Field(
        description=(
            "Classification of the SPARQL query type expressed by the question. "
            "Must be exactly one of the allowed values."
        ),
    )


# FEW-SHOT EXAMPLES -----------------------------------------------------------

class HumanPrompt(BaseModel):
    question: str


class FewShotExample(BaseModel):
    human_prompt: HumanPrompt
    ai_response: LLMExtractedInfo


FEW_SHOT_EXAMPLES: list[FewShotExample] = [
    # 1. SINGLE_FACT --------------------------------------------------------
    FewShotExample(
        human_prompt=HumanPrompt(
            question="What are the papers written by the person Sabrina Senatore?",
        ),
        ai_response=LLMExtractedInfo(
            explanation=(
                "1. The user asks for the papers authored by one specific person.\n"
                "2. Named entities: 'Sabrina Senatore' (person).\n"
                "3. Query type: SINGLE_FACT — single piece of information about one author, "
                "no chaining, no count, no negation."
            ),
            named_entities=[
                LLMNamedEntity(name="Sabrina Senatore", type="person"),
            ],
            query_type="SINGLE_FACT",
        ),
    ),
    # 2. MULTI_FACT ---------------------------------------------------------
    FewShotExample(
        human_prompt=HumanPrompt(
            question="In which venues has Wazir Muhammad published?",
        ),
        ai_response=LLMExtractedInfo(
            explanation=(
                "1. The user asks for the venues where a specific author published.\n"
                "2. Named entities: 'Wazir Muhammad' (person).\n"
                "3. Query type: MULTI_FACT — answer requires chaining through an intermediate "
                "variable (publications) to reach the venue."
            ),
            named_entities=[
                LLMNamedEntity(name="Wazir Muhammad", type="person"),
            ],
            query_type="MULTI_FACT",
        ),
    ),
    # 3. DOUBLE_INTENT ------------------------------------------------------
    FewShotExample(
        human_prompt=HumanPrompt(
            question="Mention the papers published by Wazir Muhammad and in which year.",
        ),
        ai_response=LLMExtractedInfo(
            explanation=(
                "1. The user asks for two related pieces of information: papers AND their year.\n"
                "2. Named entities: 'Wazir Muhammad' (person).\n"
                "3. Query type: DOUBLE_INTENT — the conjunction 'and in which year' couples "
                "two answers (publication, year) per result."
            ),
            named_entities=[
                LLMNamedEntity(name="Wazir Muhammad", type="person"),
            ],
            query_type="DOUBLE_INTENT",
        ),
    ),
    # 4. BOOLEAN ------------------------------------------------------------
    FewShotExample(
        human_prompt=HumanPrompt(
            question="Did Ming-Wang Cheng publish the paper 'Individual Cell Equalization for Series Connected Lithium-Ion Batteries'?",
        ),
        ai_response=LLMExtractedInfo(
            explanation=(
                "1. Yes/no question about an authorship fact.\n"
                "2. Named entities: 'Ming-Wang Cheng' (person), 'Individual Cell Equalization "
                "for Series Connected Lithium-Ion Batteries' (publication).\n"
                "3. Query type: BOOLEAN — starts with 'Did', no negation cues."
            ),
            named_entities=[
                LLMNamedEntity(name="Ming-Wang Cheng", type="person"),
                LLMNamedEntity(
                    name="Individual Cell Equalization for Series Connected Lithium-Ion Batteries",
                    type="publication",
                ),
            ],
            query_type="BOOLEAN",
        ),
    ),
    # 5. NEGATION -----------------------------------------------------------
    FewShotExample(
        human_prompt=HumanPrompt(
            question="Was the paper 'A Priority Queue Transform' not published by the person Michael L. Fredman?",
        ),
        ai_response=LLMExtractedInfo(
            explanation=(
                "1. Yes/no question with one 'not' (single negation).\n"
                "2. Named entities: 'A Priority Queue Transform' (publication), "
                "'Michael L. Fredman' (person).\n"
                "3. Query type: NEGATION — exactly one negation marker."
            ),
            named_entities=[
                LLMNamedEntity(name="A Priority Queue Transform", type="publication"),
                LLMNamedEntity(name="Michael L. Fredman", type="person"),
            ],
            query_type="NEGATION",
        ),
    ),
    # 6. DOUBLE_NEGATION ----------------------------------------------------
    FewShotExample(
        human_prompt=HumanPrompt(
            question="Wasn't the paper 'Modeling Syntactic Complexity with P Systems: A Preview' not not published by the person named Benedek Nagy?",
        ),
        ai_response=LLMExtractedInfo(
            explanation=(
                "1. Yes/no question containing the surface marker 'not not'. "
                "The two consecutive 'not's cancel out, so the intent is positive.\n"
                "2. Named entities: 'Modeling Syntactic Complexity with P Systems: A Preview' "
                "(publication), 'Benedek Nagy' (person).\n"
                "3. Query type: DOUBLE_NEGATION — explicit 'not not' double-negation construct."
            ),
            named_entities=[
                LLMNamedEntity(
                    name="Modeling Syntactic Complexity with P Systems: A Preview",
                    type="publication",
                ),
                LLMNamedEntity(name="Benedek Nagy", type="person"),
            ],
            query_type="DOUBLE_NEGATION",
        ),
    ),
    # 7. UNION --------------------------------------------------------------
    FewShotExample(
        human_prompt=HumanPrompt(
            question="In VL/HCC and Comput. Music. J., what papers did S. Conversy publish?",
        ),
        ai_response=LLMExtractedInfo(
            explanation=(
                "1. The user asks for papers by an author appearing in either of two venues.\n"
                "2. Named entities: 'VL/HCC' (venue), 'Comput. Music. J.' (venue), "
                "'S. Conversy' (person).\n"
                "3. Query type: UNION — the two venues are listed as alternatives "
                "(papers in venue A or venue B), with the author constraint shared by both branches."
            ),
            named_entities=[
                LLMNamedEntity(name="VL/HCC", type="venue"),
                LLMNamedEntity(name="Comput. Music. J.", type="venue"),
                LLMNamedEntity(name="S. Conversy", type="person"),
            ],
            query_type="UNION",
        ),
    ),
    # 8. COUNT --------------------------------------------------------------
    FewShotExample(
        human_prompt=HumanPrompt(
            question="Report the count of papers that Fanggang Wang has published in IEEE Wirel. Commun..",
        ),
        ai_response=LLMExtractedInfo(
            explanation=(
                "1. The user asks for a number of papers ('count of papers').\n"
                "2. Named entities: 'Fanggang Wang' (person), 'IEEE Wirel. Commun.' (venue).\n"
                "3. Query type: COUNT — explicit 'count of' aggregation cue."
            ),
            named_entities=[
                LLMNamedEntity(name="Fanggang Wang", type="person"),
                LLMNamedEntity(name="IEEE Wirel. Commun.", type="venue"),
            ],
            query_type="COUNT",
        ),
    ),
    # 9. SUPERLATIVE+COMPARATIVE -------------------------------------------
    FewShotExample(
        human_prompt=HumanPrompt(
            question="When was the first paper by Tom Tollenaere published?",
        ),
        ai_response=LLMExtractedInfo(
            explanation=(
                "1. The user asks for the earliest publication year of an author.\n"
                "2. Named entities: 'Tom Tollenaere' (person).\n"
                "3. Query type: SUPERLATIVE+COMPARATIVE — 'first' is a superlative cue."
            ),
            named_entities=[
                LLMNamedEntity(name="Tom Tollenaere", type="person"),
            ],
            query_type="SUPERLATIVE+COMPARATIVE",
        ),
    ),
    # 10. DISAMBIGUATION ---------------------------------------------------
    FewShotExample(
        human_prompt=HumanPrompt(
            question="Mention the publication on neural networks that Sabrina Senatore published in ECAI.",
        ),
        ai_response=LLMExtractedInfo(
            explanation=(
                "1. The user asks for one specific publication, narrowed down by author and venue, "
                "with the topic phrase 'on neural networks' as the disambiguating cue. "
                "'neural networks' is a topic description, not a publication title, so it is "
                "NOT extracted as a named entity.\n"
                "2. Named entities: 'Sabrina Senatore' (person), 'ECAI' (venue).\n"
                "3. Query type: DISAMBIGUATION — the topic phrase 'on neural networks' "
                "is used as a disambiguating constraint."
            ),
            named_entities=[
                LLMNamedEntity(name="Sabrina Senatore", type="person"),
                LLMNamedEntity(name="ECAI", type="venue"),
            ],
            query_type="DISAMBIGUATION",
        ),
    ),
]
