# ruff: noqa: E501

from typing import Any

import yaml
from pydantic import BaseModel, Field

from dblp_kgqa import SchemaVersion
from dblp_kgqa.modules.schemas import (
    LinkedEntities,
    LinkedEntity,
    LinkedRelation,
)

# SYSTEM PROMPT ---------------------------------------------------------------

FULL_SYSTEM_PROMPT = """You are an expert SPARQL engineer specialized in the DBLP bibliographic database.
Translate the user's natural language question into a correct SPARQL query.

### INPUT CONTEXT (from the user message)
- **Entities**: {entities_description}
- **Relations**: {relations_description}

### RULE 1 — TARGET VARIABLES
Bind the query result to these variable names in the SELECT clause:
- Single-answer fact retrieval → `?answer`
- Questions asking for two related pieces of information → `?firstanswer` and `?secondanswer`
- Counting → `(COUNT(DISTINCT ?answer) AS ?count)`, or `(AVG(?count) AS ?answer)` for averages of counts
Do not substitute descriptive names like `?year`, `?venue`, `?pub`, `?coauthor` — use only the variable names listed above.

### RULE 2 — PREDICATE DIRECTION
The DBLP ontology uses PASSIVE predicates: a triple about a Publication has the Publication as SUBJECT, not as object.
- `<Publication> <authoredBy> <Person>` — CORRECT
- `<Person> <authoredBy> <Publication>` — WRONG (this direction does not exist)
{venue_predicate_example}
- `<Publication> <yearOfPublication> 'YYYY'` — CORRECT
The subject is the Person for predicates describing the person directly (e.g., `primaryAffiliation`, `webpage`, `wikidata`, `orcid`).
When answering "papers by person X", `?answer` is the Publication: `?answer <authoredBy> <person_uri>`.

### RULE 3 — URIS
Write URIs as full IRIs in angle brackets (e.g. `<https://dblp.org/pid/78/4247>`). Never use namespace prefixes like `dblp:authoredBy`.
Use only URIs that appear in the `entities` or `relations` fields of the current question. Do not invent URIs.

### RULE 4 — VENUES
{venue_rule}

### RULE 5 — NEGATION IN BOOLEAN QUERIES
BOOLEAN questions involving negation use one of two structural forms:
- **Tautology form** — the fact triples appear in the outer ASK body AND are repeated inside a `FILTER NOT EXISTS`; the FILTER must repeat the ENTIRE set of triples, not just one. Example with two triples:
  `ASK {{ ?x <authoredBy> <P> . ?x <publishedIn> 'V' FILTER NOT EXISTS {{ ?x <authoredBy> <P> . ?x <publishedIn> 'V' }} }}`
- **Plain form** — a positive ASK with no FILTER:
  `ASK {{ <triple pattern> }}`

### RULE 6 — TEMPORAL
For relative time frames like "in the last N years", use `FILTER(xsd:integer(?year) >= YEAR(NOW()) - N)`. Do not hardcode specific years.

### RULE 7 — UNION
Wrap each branch in its own curly braces: `{{ branch1 }} UNION {{ branch2 }}`.
Constraints that apply to BOTH branches (e.g. an author filter shared by both) go OUTSIDE the UNION, not inside each branch.

### RULE 8 — QUERY FORMAT
Use `SELECT DISTINCT ... WHERE {{ ... }}` for fact retrieval and `ASK {{ ... }}` for yes/no questions.
Do not emit `ASK {{ SELECT ... }}` or `ASK {{ ... MINUS ... }}`.
"""


VENUE_PREDICATE_EXAMPLES: dict[SchemaVersion, str] = {
    "dblp_quad": """\
- `<Publication> <publishedIn> 'Venue Name'` — CORRECT""",
    "current": """\
- `<Publication> <publishedIn> 'Venue Name'` — CORRECT (venue as literal string)
- `<Publication> <publishedInStream> <Stream URI>` — CORRECT (venue as URI entity)""",
}

VENUE_RULES: dict[SchemaVersion, str] = {
    "dblp_quad": """\
Venue names MUST be literal strings with `publishedIn`. NEVER use venue URIs or `publishedInStream`.
When a venue is provided as an entity, its URI is empty and its name is in the `name` field — use that name as the literal:
`?x <https://dblp.org/rdf/schema#publishedIn> 'VenueName'`.
When a venue is not in the entities list, take its name verbatim from the question text and use it as the literal.""",
    "current": """\
Venues can appear in two forms depending on the linked entities input:
- **Venue with URI** (type='venue', uri is non-empty): use `publishedInStream` with the full URI in angle brackets.
  Example: `?x <https://dblp.org/rdf/schema#publishedInStream> <https://dblp.org/streams/conf/ecai>`.
- **Venue as literal** (type='venue', uri is empty): use `publishedIn` with the name as a literal string.
  Example: `?x <https://dblp.org/rdf/schema#publishedIn> 'ECAI'`.
Choose the correct predicate based on whether the venue entity has a URI or not.""",
}

# Structured Output -----------------------------------------------------------

class LLMGeneratedQueryExp(BaseModel):
    explanation: str = Field(
        description=(
            "Step-by-step reasoning: identify the query type and target variable, "
            "map entities to triple patterns with correct predicate direction, "
            "and note any special constructs needed. Be concise."
        ),
        max_length=1200,
    )
    query: str = Field(
        description=(
            "The final SPARQL query, syntactically correct and ready for execution. "
            "Must contain ONLY raw SPARQL code without markdown formatting."
        )
    )


class LLMGeneratedQuery(BaseModel):
    query: str = Field(
        description=(
            "The final SPARQL query, syntactically correct and ready for execution. "
            "Must contain ONLY raw SPARQL code without markdown formatting."
        )
    )

# Few shot examples -----------------------------------------------------------

class HumanPrompt(BaseModel):
    question: str
    entities: LinkedEntities
    relations: LinkedRelation

    def to_yaml_str(self, **yaml_kwargs: Any) -> str:
        data = self.model_dump(mode="json")
        return yaml.dump(data, sort_keys=False, **yaml_kwargs)


class FewShotExample(BaseModel):
    human_prompt: HumanPrompt
    ai_response: LLMGeneratedQueryExp


FEW_SHOT_EXAMPLES: list[FewShotExample] = [
    # 1. SINGLE_FACT — papers by person ---------------------------------------
    FewShotExample(
        human_prompt=HumanPrompt(
            question="What are the papers written by the person Sabrina Senatore?",
            entities=LinkedEntities(
                linked_entities=[
                    LinkedEntity(
                        name="",
                        uri="<https://dblp.org/pid/78/4247>",
                        type="person",
                    )
                ]
            ),
            relations=LinkedRelation(
                schema_context=["<https://dblp.org/rdf/schema#authoredBy>"]
            ),
        ),
        ai_response=LLMGeneratedQueryExp(
            explanation=(
                "1. Query type: SINGLE_FACT. Target variable: ?answer.\n"
                "2. ?answer (publication) --authoredBy--> <https://dblp.org/pid/78/4247> (person). "
                "Retrieves all publications by the given author."
            ),
            query="SELECT DISTINCT ?answer WHERE { ?answer <https://dblp.org/rdf/schema#authoredBy> <https://dblp.org/pid/78/4247> . }",
        ),
    ),
    # 2. MULTI_FACT — venues where person published ---------------------------
    FewShotExample(
        human_prompt=HumanPrompt(
            question="In which venues has Wazir Muhammad published?",
            entities=LinkedEntities(
                linked_entities=[
                    LinkedEntity(
                        name="",
                        uri="<https://dblp.org/pid/211/3355>",
                        type="person",
                    )
                ]
            ),
            relations=LinkedRelation(
                schema_context=[
                    "<https://dblp.org/rdf/schema#authoredBy>",
                    "<https://dblp.org/rdf/schema#publishedIn>",
                ]
            ),
        ),
        ai_response=LLMGeneratedQueryExp(
            explanation=(
                "1. Query type: MULTI_FACT. Target variable: ?answer (the venue).\n"
                "2. ?x (publication, intermediate) --authoredBy--> <https://dblp.org/pid/211/3355> (person). "
                "Finds all publications by Wazir Muhammad.\n"
                "3. ?x (same publication) --publishedIn--> ?answer (venue literal). "
                "Chains to get the venue name for each publication."
            ),
            query=(
                "SELECT DISTINCT ?answer WHERE { "
                "?x <https://dblp.org/rdf/schema#authoredBy> <https://dblp.org/pid/211/3355> . "
                "?x <https://dblp.org/rdf/schema#publishedIn> ?answer }"
            ),
        ),
    ),
    # 3. DOUBLE_INTENT — papers and their years -------------------------------
    FewShotExample(
        human_prompt=HumanPrompt(
            question="Mention the papers published by Wazir Muhammad and in which year.",
            entities=LinkedEntities(
                linked_entities=[
                    LinkedEntity(
                        name="",
                        uri="<https://dblp.org/pid/211/3355>",
                        type="person",
                    )
                ]
            ),
            relations=LinkedRelation(
                schema_context=[
                    "<https://dblp.org/rdf/schema#authoredBy>",
                    "<https://dblp.org/rdf/schema#yearOfPublication>",
                ]
            ),
        ),
        ai_response=LLMGeneratedQueryExp(
            explanation=(
                "1. Query type: DOUBLE_INTENT. Target variables: ?firstanswer (publication), ?secondanswer (year).\n"
                "2. ?firstanswer (publication) --authoredBy--> <https://dblp.org/pid/211/3355> (person). "
                "Finds publications by Wazir Muhammad.\n"
                "3. ?firstanswer --yearOfPublication--> ?secondanswer. "
                "Chains to get the year for each publication."
            ),
            query=(
                "SELECT DISTINCT ?firstanswer ?secondanswer WHERE { "
                "?firstanswer <https://dblp.org/rdf/schema#authoredBy> <https://dblp.org/pid/211/3355> . "
                "?firstanswer <https://dblp.org/rdf/schema#yearOfPublication> ?secondanswer }"
            ),
        ),
    ),
    # 4. BOOLEAN — did X publish paper Y? -------------------------------------
    FewShotExample(
        human_prompt=HumanPrompt(
            question="Did Ming-Wang Cheng publish the paper 'Individual Cell Equalization for Series Connected Lithium-Ion Batteries'?",
            entities=LinkedEntities(
                linked_entities=[
                    LinkedEntity(
                        name="",
                        uri="<https://dblp.org/rec/journals/ieicet/LeeCYH06>",
                        type="publication",
                    ),
                    LinkedEntity(
                        name="",
                        uri="<https://dblp.org/pid/13/6180>",
                        type="person",
                    ),
                ]
            ),
            relations=LinkedRelation(
                schema_context=["<https://dblp.org/rdf/schema#authoredBy>"]
            ),
        ),
        ai_response=LLMGeneratedQueryExp(
            explanation=(
                "1. Query type: BOOLEAN. Use ASK query.\n"
                "2. <https://dblp.org/rec/journals/ieicet/LeeCYH06> (publication) --authoredBy--> "
                "<https://dblp.org/pid/13/6180> (person). Checks if the authorship relation exists."
            ),
            query="ASK { <https://dblp.org/rec/journals/ieicet/LeeCYH06> <https://dblp.org/rdf/schema#authoredBy> <https://dblp.org/pid/13/6180> }",
        ),
    ),
    # 5. NEGATION — has X NOT published Y? ------------------------------------
    FewShotExample(
        human_prompt=HumanPrompt(
            question="Was the paper 'A Priority Queue Transform' not published by the person Michael L. Fredman?",
            entities=LinkedEntities(
                linked_entities=[
                    LinkedEntity(
                        name="",
                        uri="<https://dblp.org/rec/conf/wae/Fredman99>",
                        type="publication",
                    ),
                    LinkedEntity(
                        name="",
                        uri="<https://dblp.org/pid/15/454>",
                        type="person",
                    ),
                ]
            ),
            relations=LinkedRelation(
                schema_context=["<https://dblp.org/rdf/schema#authoredBy>"]
            ),
        ),
        ai_response=LLMGeneratedQueryExp(
            explanation=(
                "0. Question contains exactly one 'not' -> single negation -> FILTER NOT EXISTS.\n"
                "1. Query type: NEGATION. Use ASK with FILTER NOT EXISTS.\n"
                "2. Outer pattern: <https://dblp.org/rec/conf/wae/Fredman99> --authoredBy--> "
                "<https://dblp.org/pid/15/454>. States the fact to check.\n"
                "3. FILTER NOT EXISTS repeats the same pattern inside. If the fact exists, "
                "FILTER eliminates it, leaving no solutions -> ASK returns false."
            ),
            query=(
                "ASK { <https://dblp.org/rec/conf/wae/Fredman99> <https://dblp.org/rdf/schema#authoredBy> <https://dblp.org/pid/15/454> "
                "FILTER NOT EXISTS { <https://dblp.org/rec/conf/wae/Fredman99> <https://dblp.org/rdf/schema#authoredBy> <https://dblp.org/pid/15/454> } }"
            ),
        ),
    ),
    # 6. DOUBLE_NEGATION — "not not" = positive -------------------------------
    FewShotExample(
        human_prompt=HumanPrompt(
            question="Wasn't the paper 'Modeling Syntactic Complexity with P Systems: A Preview' not not published by the person named Benedek Nagy?",
            entities=LinkedEntities(
                linked_entities=[
                    LinkedEntity(
                        name="",
                        uri="<https://dblp.org/rec/conf/uc/EnguixN14>",
                        type="publication",
                    ),
                    LinkedEntity(
                        name="",
                        uri="<https://dblp.org/pid/06/6134>",
                        type="person",
                    ),
                ]
            ),
            relations=LinkedRelation(
                schema_context=["<https://dblp.org/rdf/schema#authoredBy>"]
            ),
        ),
        ai_response=LLMGeneratedQueryExp(
            explanation=(
                "0. Question contains two 'not's -> they cancel out -> plain ASK, no FILTER NOT EXISTS.\n"
                "1. Query type: DOUBLE_NEGATION. Double negation cancels out -> treat as positive BOOLEAN.\n"
                "2. <https://dblp.org/rec/conf/uc/EnguixN14> (publication) --authoredBy--> "
                "<https://dblp.org/pid/06/6134> (person). Simple ASK, no FILTER NOT EXISTS needed."
            ),
            query=(
                "ASK { <https://dblp.org/rec/conf/uc/EnguixN14> "
                "<https://dblp.org/rdf/schema#authoredBy> <https://dblp.org/pid/06/6134> }"
            ),
        ),
    ),
    # 7. UNION — papers by person in two venues ------------------------------
    FewShotExample(
        human_prompt=HumanPrompt(
            question="In VL/HCC and Comput. Music. J., what papers did S. Conversy publish?",
            entities=LinkedEntities(
                linked_entities=[
                    LinkedEntity(
                        name="",
                        uri="<https://dblp.org/pid/42/4104>",
                        type="person",
                    ),
                    LinkedEntity(name="VL/HCC", uri="", type="venue"),
                    LinkedEntity(
                        name="Comput. Music. J.", uri="", type="venue"
                    ),
                ]
            ),
            relations=LinkedRelation(
                schema_context=[
                    "<https://dblp.org/rdf/schema#authoredBy>",
                    "<https://dblp.org/rdf/schema#publishedIn>",
                ]
            ),
        ),
        ai_response=LLMGeneratedQueryExp(
            explanation=(
                "1. Query type: UNION. Target variable: ?answer (the publications).\n"
                "2. ?answer --authoredBy--> <https://dblp.org/pid/42/4104> (person). "
                "The author constraint is placed OUTSIDE the UNION because it applies to both branches.\n"
                "3. Branch 1: ?answer --publishedIn--> 'VL/HCC'. Papers in first venue.\n"
                "4. Branch 2: ?answer --publishedIn--> 'Comput. Music. J.'. Papers in second venue.\n"
                "5. Each venue branch wrapped in its own { }. Venues are literal strings (no URIs)."
            ),
            query=(
                "SELECT DISTINCT ?answer WHERE { "
                "?answer <https://dblp.org/rdf/schema#authoredBy> <https://dblp.org/pid/42/4104> . "
                "{ ?answer <https://dblp.org/rdf/schema#publishedIn> 'VL/HCC' } "
                "UNION "
                "{ ?answer <https://dblp.org/rdf/schema#publishedIn> 'Comput. Music. J.' } }"
            ),
        ),
    ),
    # 8. COUNT — how many papers by X? ---------------------------------------
    FewShotExample(
        human_prompt=HumanPrompt(
            question="Report the count of papers that Fanggang Wang has published in IEEE Wirel. Commun..",
            entities=LinkedEntities(
                linked_entities=[
                    LinkedEntity(
                        name="",
                        uri="<https://dblp.org/pid/84/2752>",
                        type="person",
                    ),
                    LinkedEntity(
                        name="IEEE Wirel. Commun.", uri="", type="venue"
                    ),
                ]
            ),
            relations=LinkedRelation(
                schema_context=[
                    "<https://dblp.org/rdf/schema#authoredBy>",
                    "<https://dblp.org/rdf/schema#publishedIn>",
                ]
            ),
        ),
        ai_response=LLMGeneratedQueryExp(
            explanation=(
                "1. Query type: COUNT. Target variable: (COUNT(DISTINCT ?answer) AS ?count).\n"
                "2. ?answer (publication) --authoredBy--> <https://dblp.org/pid/84/2752> (person). "
                "Finds publications by the author.\n"
                "3. ?answer --publishedIn--> 'IEEE Wirel. Commun.' (venue literal). Filters to the specific venue.\n"
                "4. COUNT(DISTINCT ?answer) counts the unique publications matching both constraints."
            ),
            query=(
                "SELECT (COUNT(DISTINCT ?answer) AS ?count) WHERE { "
                "?answer <https://dblp.org/rdf/schema#authoredBy> <https://dblp.org/pid/84/2752> . "
                "?answer <https://dblp.org/rdf/schema#publishedIn> 'IEEE Wirel. Commun.' }"
            ),
        ),
    ),
    # 9. SUPERLATIVE — first publication year (MIN) --------------------------
    FewShotExample(
        human_prompt=HumanPrompt(
            question="When was the first paper by Tom Tollenaere published?",
            entities=LinkedEntities(
                linked_entities=[
                    LinkedEntity(
                        name="",
                        uri="<https://dblp.org/pid/44/6536>",
                        type="person",
                    )
                ]
            ),
            relations=LinkedRelation(
                schema_context=[
                    "<https://dblp.org/rdf/schema#authoredBy>",
                    "<https://dblp.org/rdf/schema#yearOfPublication>",
                ]
            ),
        ),
        ai_response=LLMGeneratedQueryExp(
            explanation=(
                "1. Query type: SUPERLATIVE. Target variable: ?answer (the earliest year).\n"
                "2. ?x (publication) --authoredBy--> <https://dblp.org/pid/44/6536> (person). "
                "Finds publications by Tom Tollenaere.\n"
                "3. ?x --yearOfPublication--> ?answer. Gets the year for each publication.\n"
                "4. MIN(xsd:integer(?answer)) selects the earliest year by casting to integer "
                "and taking the minimum."
            ),
            query=(
                "SELECT DISTINCT MIN(xsd:integer(?answer)) AS ?answer WHERE { "
                "?x <https://dblp.org/rdf/schema#authoredBy> <https://dblp.org/pid/44/6536> . "
                "?x <https://dblp.org/rdf/schema#yearOfPublication> ?answer }"
            ),
        ),
    ),
    # 10. DISAMBIGUATION — paper by person in venue --------------------------
    FewShotExample(
        human_prompt=HumanPrompt(
            question="Mention the publication on neural networks that Sabrina Senatore published in ECAI.",
            entities=LinkedEntities(
                linked_entities=[
                    LinkedEntity(
                        name="",
                        uri="<https://dblp.org/pid/78/4247>",
                        type="person",
                    ),
                    LinkedEntity(name="ECAI", uri="", type="venue"),
                ]
            ),
            relations=LinkedRelation(
                schema_context=[
                    "<https://dblp.org/rdf/schema#authoredBy>",
                    "<https://dblp.org/rdf/schema#publishedIn>",
                ]
            ),
        ),
        ai_response=LLMGeneratedQueryExp(
            explanation=(
                "1. Query type: DISAMBIGUATION. Target variable: ?answer (the publication).\n"
                "2. ?answer (publication) --authoredBy--> <https://dblp.org/pid/78/4247> (person). "
                "Filters by author.\n"
                "3. ?answer --publishedIn--> 'ECAI' (venue literal). "
                "Narrows down to the specific venue to disambiguate."
            ),
            query=(
                "SELECT DISTINCT ?answer WHERE { "
                "?answer <https://dblp.org/rdf/schema#authoredBy> <https://dblp.org/pid/78/4247> . "
                "?answer <https://dblp.org/rdf/schema#publishedIn> 'ECAI' }"
            ),
        ),
    ),
]