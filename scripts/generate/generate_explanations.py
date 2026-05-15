# ruff: noqa: E501

import json
import logging
import sys

from pydantic import BaseModel, Field

from dblp_kgqa import PROJECT_ROOT
from dblp_kgqa.services.dblp_quad import (
    QUERY_TYPE,
    DblpQuadService,
    DblpQuadServiceConfig,
)
from dblp_kgqa.services.llm import (
    GoogleBackendConfig,
    LLMService,
    LLMServiceConfig,
    PromptMessage,
)

logger = logging.getLogger(__name__)

# CONFIG ----------------------------------------------------------------------
_EXPLANATIONS_PATH = "data/dblp_quad/train/explanations.json"

SYSTEM_PROMPT = """You are generating reasoning traces for a KGQA training dataset (DBLP-QuAD).
These traces will be used as few-shot examples for a SMALL language model (4B params) that must learn to generate SPARQL queries from natural language questions over the DBLP ontology.

I will provide you with a User Question, the Query Type, Entities, Relations, and the Gold Standard SPARQL query.
Your job is to write a concise, step-by-step reasoning trace that explains HOW to construct that SPARQL query from the question.

### OUTPUT FORMAT — follow this numbered-step structure strictly:
1. State the query type and the target variable(s).
2. For each triple pattern in the query, explain the direction: which node is the subject, which predicate is used, and which node is the object. Use the notation: `subject --predicate--> object`.
3. If the query uses special constructs (FILTER NOT EXISTS, UNION, BIND(IF), MIN/MAX, GROUP_CONCAT, COUNT, AVG, subqueries), explain WHY that construct is needed based on the user's intent.
4. Keep the total explanation between 2 and 5 numbered steps. Be concise.

### DBLP ONTOLOGY — CRITICAL PREDICATE DIRECTION:
The DBLP ontology uses PASSIVE predicates. The subject is ALWAYS the Publication (except for person-level properties).
- `<Publication> --authoredBy--> <Person>` — CORRECT (publication is the subject)
- `<Person> --authoredBy--> <Publication>` — WRONG (this does NOT exist)
- `<Publication> --publishedIn--> 'Venue Name'` — CORRECT (venue is a literal string)
- `<Publication> --yearOfPublication--> 'YYYY'` — CORRECT
- `<Publication> --title--> 'Title'` — CORRECT
- `<Publication> --numberOfCreators--> count` — CORRECT
- `<Person> --primaryAffiliation--> 'Institution'` — CORRECT (exception: person is subject)
- `<Person> --webpage--> <URL>` — CORRECT (exception: person is subject)
- `<Person> --wikidata--> <URI>` — CORRECT (exception: person is subject)
- `<Person> --orcid--> 'ORCID'` — CORRECT (exception: person is subject)

### SELF-VERIFICATION:
Before finalizing, mentally verify:
- Does each triple pattern in my explanation correspond to a triple in the SPARQL query?
- Is the predicate direction correct?
- Did I identify the correct target variable(s)?

Write ONLY the numbered reasoning steps. Do not rewrite the SPARQL query.
"""

FEW_SHOT_MESSAGES: dict[QUERY_TYPE, list[PromptMessage]] = {
    # 1. SINGLE_FACT ----------------------------------------------------------
    "SINGLE_FACT": [
        PromptMessage(
            role="human",
            content=(
                "**Query Type**: SINGLE_FACT\n"
                "**Question**: What are the papers written by the person Sabrina Senatore?\n"
                "**Entities**: <https://dblp.org/pid/78/4247>\n"
                "**Relations**: <https://dblp.org/rdf/schema#authoredBy>\n"
                "**GOLD SPARQL**: SELECT DISTINCT ?answer WHERE { ?answer <https://dblp.org/rdf/schema#authoredBy> <https://dblp.org/pid/78/4247> . }"
            ),
        ),
        PromptMessage(
            role="ai",
            content=json.dumps(
                {
                    "explanation": (
                        "1. Query type: SINGLE_FACT. Target variable: ?answer.\n"
                        "2. ?answer (publication) --authoredBy--> <https://dblp.org/pid/78/4247> (person). The publication is the subject.\n"
                        "3. No special constructs needed."
                    )
                }
            ),
        ),
    ],
    # 2. MULTI_FACT -----------------------------------------------------------
    "MULTI_FACT": [
        PromptMessage(
            role="human",
            content=(
                "**Query Type**: MULTI_FACT\n"
                "**Question**: In which venues has Wazir Muhammad published?\n"
                "**Entities**: <https://dblp.org/pid/211/3355>\n"
                "**Relations**: <https://dblp.org/rdf/schema#authoredBy>, <https://dblp.org/rdf/schema#publishedIn>\n"
                "**GOLD SPARQL**: SELECT DISTINCT ?answer WHERE { ?x <https://dblp.org/rdf/schema#authoredBy> <https://dblp.org/pid/211/3355> . ?x <https://dblp.org/rdf/schema#publishedIn> ?answer }"
            ),
        ),
        PromptMessage(
            role="ai",
            content=json.dumps(
                {
                    "explanation": (
                        "1. Query type: MULTI_FACT. Target variable: ?answer (the venue).\n"
                        "2. ?x (publication, intermediate) --authoredBy--> <https://dblp.org/pid/211/3355> (person). Finds all publications by the person.\n"
                        "3. ?x (same publication) --publishedIn--> ?answer (venue literal). Chains to get the venue name.\n"
                        "4. No special constructs needed."
                    )
                }
            ),
        ),
    ],
    # 3. DOUBLE_INTENT --------------------------------------------------------
    "DOUBLE_INTENT": [
        PromptMessage(
            role="human",
            content=(
                "**Query Type**: DOUBLE_INTENT\n"
                "**Question**: Name the co-authors of Dingxuan Li and where are they affiliated?\n"
                "**Entities**: <https://dblp.org/pid/300/8467>\n"
                "**Relations**: <https://dblp.org/rdf/schema#authoredBy>, <https://dblp.org/rdf/schema#primaryAffiliation>\n"
                "**GOLD SPARQL**: SELECT DISTINCT ?firstanswer ?secondanswer WHERE { "
                "?x <https://dblp.org/rdf/schema#authoredBy> <https://dblp.org/pid/300/8467> . "
                "?x <https://dblp.org/rdf/schema#authoredBy> ?firstanswer . "
                "FILTER(?firstanswer != <https://dblp.org/pid/300/8467>) . "
                "?firstanswer <https://dblp.org/rdf/schema#primaryAffiliation> ?secondanswer }"
            ),
        ),
        PromptMessage(
            role="ai",
            content=json.dumps(
                {
                    "explanation": (
                        "1. Query type: DOUBLE_INTENT. Target variables: ?firstanswer (co-author), ?secondanswer (affiliation).\n"
                        "2. ?x (publication, intermediate) --authoredBy--> <https://dblp.org/pid/300/8467> (person). Finds publications by the person.\n"
                        "3. ?x (same publication) --authoredBy--> ?firstanswer (co-author). Finds all authors of those publications.\n"
                        "4. FILTER excludes the original person from co-authors. ?firstanswer (person) --primaryAffiliation--> ?secondanswer (institution). Person is subject here (exception).\n"
                        "5. Two pieces of info requested: co-authors + affiliations, so we use ?firstanswer and ?secondanswer."
                    )
                }
            ),
        ),
    ],
    # 4. BOOLEAN --------------------------------------------------------------
    "BOOLEAN": [
        PromptMessage(
            role="human",
            content=(
                "**Query Type**: BOOLEAN\n"
                "**Question**: Did Wanlei Zhou and Chowdhury, Morshed U. co-author the paper 'MVGL Analyser for Multi-classifier Based Spam Filtering System'?\n"
                "**Entities**: <https://dblp.org/pid/92/2939>, <https://dblp.org/pid/74/4874>, <https://dblp.org/rec/conf/ACISicis/IslamZC09>\n"
                "**Relations**: <https://dblp.org/rdf/schema#authoredBy>\n"
                "**GOLD SPARQL**: ASK { <https://dblp.org/rec/conf/ACISicis/IslamZC09> <https://dblp.org/rdf/schema#authoredBy> <https://dblp.org/pid/92/2939> . "
                "<https://dblp.org/rec/conf/ACISicis/IslamZC09> <https://dblp.org/rdf/schema#authoredBy> <https://dblp.org/pid/74/4874> }"
            ),
        ),
        PromptMessage(
            role="ai",
            content=json.dumps(
                {
                    "explanation": (
                        "1. Query type: BOOLEAN. Use ASK (yes/no question).\n"
                        "2. <publication> --authoredBy--> <https://dblp.org/pid/92/2939> (person 1). Publication is subject.\n"
                        "3. <publication> --authoredBy--> <https://dblp.org/pid/74/4874> (person 2). Same publication must be authored by both.\n"
                        "4. No special constructs. Both triples must match for ASK to return true."
                    )
                }
            ),
        ),
    ],
    # 5. NEGATION -------------------------------------------------------------
    "NEGATION": [
        PromptMessage(
            role="human",
            content=(
                "**Query Type**: NEGATION\n"
                "**Question**: Has Ming-Wang Cheng not published the paper 'Individual Cell Equalization for Series Connected Lithium-Ion Batteries'?\n"
                "**Entities**: <https://dblp.org/rec/journals/ieicet/LeeCYH06>, <https://dblp.org/pid/13/6180>\n"
                "**Relations**: <https://dblp.org/rdf/schema#authoredBy>\n"
                "**GOLD SPARQL**: ASK { <https://dblp.org/rec/journals/ieicet/LeeCYH06> <https://dblp.org/rdf/schema#authoredBy> <https://dblp.org/pid/13/6180> "
                "FILTER NOT EXISTS { <https://dblp.org/rec/journals/ieicet/LeeCYH06> <https://dblp.org/rdf/schema#authoredBy> <https://dblp.org/pid/13/6180> } }"
            ),
        ),
        PromptMessage(
            role="ai",
            content=json.dumps(
                {
                    "explanation": (
                        "1. Query type: NEGATION. Use ASK with FILTER NOT EXISTS.\n"
                        "2. <publication> --authoredBy--> <person>. Publication is subject.\n"
                        "3. The question asks 'has X NOT published'. FILTER NOT EXISTS wraps the exact same triple pattern to negate it.\n"
                        "4. The outer pattern states the fact, FILTER NOT EXISTS repeats it — ASK returns true only if the fact does NOT exist."
                    )
                }
            ),
        ),
    ],
    # 6. DOUBLE_NEGATION ------------------------------------------------------
    "DOUBLE_NEGATION": [
        PromptMessage(
            role="human",
            content=(
                "**Query Type**: DOUBLE_NEGATION\n"
                "**Question**: Didn't Warren, James R. and Piekarski, W. not co-author a paper?\n"
                "**Entities**: <https://dblp.org/pid/00/256>, <https://dblp.org/pid/15/2169>\n"
                "**Relations**: <https://dblp.org/rdf/schema#authoredBy>\n"
                "**GOLD SPARQL**: ASK { ?x <https://dblp.org/rdf/schema#authoredBy> <https://dblp.org/pid/00/256> . "
                "?x <https://dblp.org/rdf/schema#authoredBy> <https://dblp.org/pid/15/2169> }"
            ),
        ),
        PromptMessage(
            role="ai",
            content=json.dumps(
                {
                    "explanation": (
                        "1. Query type: DOUBLE_NEGATION. 'Didn't ... not' = double negation, cancels out to positive.\n"
                        "2. Treat as plain boolean ASK. No FILTER NOT EXISTS needed.\n"
                        "3. ?x (publication) --authoredBy--> <person1> and ?x --authoredBy--> <person2>. Same publication must link to both."
                    )
                }
            ),
        ),
    ],
    # 7. UNION ----------------------------------------------------------------
    "UNION": [
        PromptMessage(
            role="human",
            content=(
                "**Query Type**: UNION\n"
                "**Question**: In VL/HCC and Comput. Music. J., what papers did S. Conversy publish?\n"
                "**Entities**: <https://dblp.org/pid/42/4104>\n"
                "**Relations**: <https://dblp.org/rdf/schema#authoredBy>, <https://dblp.org/rdf/schema#publishedIn>\n"
                "**GOLD SPARQL**: SELECT DISTINCT ?answer WHERE { ?answer <https://dblp.org/rdf/schema#authoredBy> <https://dblp.org/pid/42/4104> "
                "{ ?answer <https://dblp.org/rdf/schema#publishedIn> 'VL/HCC' } UNION { ?answer <https://dblp.org/rdf/schema#publishedIn> 'Comput. Music. J.' } }"
            ),
        ),
        PromptMessage(
            role="ai",
            content=json.dumps(
                {
                    "explanation": (
                        "1. Query type: UNION. Target variable: ?answer (publication).\n"
                        "2. ?answer (publication) --authoredBy--> <person>. Shared constraint outside UNION branches.\n"
                        "3. UNION needed because the question asks about two venues. Each branch: ?answer --publishedIn--> 'VenueName' (literal string).\n"
                        "4. Venues have no URI, so they are literal strings with publishedIn."
                    )
                }
            ),
        ),
    ],
    # 8. DISAMBIGUATION -------------------------------------------------------
    "DISAMBIGUATION": [
        PromptMessage(
            role="human",
            content=(
                "**Query Type**: DISAMBIGUATION\n"
                "**Question**: Name the venue in which Luping published the paper about Class separability.\n"
                "**Entities**: <https://dblp.org/pid/45/933>, <https://dblp.org/rec/journals/tnn/ZhouWS10>\n"
                "**Relations**: <https://dblp.org/rdf/schema#authoredBy>, <https://dblp.org/rdf/schema#publishedIn>\n"
                "**GOLD SPARQL**: SELECT DISTINCT ?answer WHERE { <https://dblp.org/rec/journals/tnn/ZhouWS10> <https://dblp.org/rdf/schema#authoredBy> <https://dblp.org/pid/45/933> . "
                "<https://dblp.org/rec/journals/tnn/ZhouWS10> <https://dblp.org/rdf/schema#publishedIn> ?answer }"
            ),
        ),
        PromptMessage(
            role="ai",
            content=json.dumps(
                {
                    "explanation": (
                        "1. Query type: DISAMBIGUATION. Target variable: ?answer (venue).\n"
                        "2. <publication> --authoredBy--> <person>. Constrains to a specific paper by a specific author (disambiguates).\n"
                        "3. <publication> --publishedIn--> ?answer (venue). Retrieves the venue of that specific paper.\n"
                        "4. Both triples use the known publication URI as subject to pin down the exact paper."
                    )
                }
            ),
        ),
    ],
    # 9. COUNT ----------------------------------------------------------------
    "COUNT": [
        PromptMessage(
            role="human",
            content=(
                "**Query Type**: COUNT\n"
                "**Question**: What is the average number of papers published by Darko Kirovski per year?\n"
                "**Entities**: <https://dblp.org/pid/81/4627>\n"
                "**Relations**: <https://dblp.org/rdf/schema#authoredBy>, <https://dblp.org/rdf/schema#yearOfPublication>\n"
                "**GOLD SPARQL**: SELECT (AVG(?count) AS ?answer) { SELECT (COUNT(?y) AS ?count) WHERE { "
                "?x <https://dblp.org/rdf/schema#authoredBy> <https://dblp.org/pid/81/4627> . "
                "?x <https://dblp.org/rdf/schema#yearOfPublication> ?y } GROUP BY ?y }"
            ),
        ),
        PromptMessage(
            role="ai",
            content=json.dumps(
                {
                    "explanation": (
                        "1. Query type: COUNT (average). Target variable: ?answer via AVG.\n"
                        "2. Inner subquery: ?x (publication) --authoredBy--> <person>. ?x --yearOfPublication--> ?y.\n"
                        "3. GROUP BY ?y groups publications by year, COUNT(?y) counts papers per year.\n"
                        "4. Outer query: AVG(?count) computes the average across all years. 'Per year' requires subquery + GROUP BY + AVG."
                    )
                }
            ),
        ),
    ],
    # 10. SUPERLATIVE+COMPARATIVE — GROUP_CONCAT variant ----------------------
    "SUPERLATIVE+COMPARATIVE": [
        PromptMessage(
            role="human",
            content=(
                "**Query Type**: SUPERLATIVE+COMPARATIVE\n"
                "**Question**: Mention the year in which Nestor R. Polanco published the most papers.\n"
                "**Entities**: <https://dblp.org/pid/202/3643>\n"
                "**Relations**: <https://dblp.org/rdf/schema#authoredBy>, <https://dblp.org/rdf/schema#yearOfPublication>\n"
                "**GOLD SPARQL**: SELECT (GROUP_CONCAT(?answer; separator=', ') AS ?answer) ?count WHERE { "
                "SELECT DISTINCT ?answer (COUNT(?answer) AS ?count) WHERE { "
                "?x <https://dblp.org/rdf/schema#authoredBy> <https://dblp.org/pid/202/3643> . "
                "?x <https://dblp.org/rdf/schema#yearOfPublication> ?answer } GROUP BY ?answer } ORDER BY DESC(?count) LIMIT 1"
            ),
        ),
        PromptMessage(
            role="ai",
            content=json.dumps(
                {
                    "explanation": (
                        "1. Query type: SUPERLATIVE+COMPARATIVE. 'Most papers' = superlative requiring aggregation.\n"
                        "2. Inner subquery: ?x (publication) --authoredBy--> <person>. ?x --yearOfPublication--> ?answer (year).\n"
                        "3. GROUP BY ?answer groups by year, COUNT(?answer) counts papers per year.\n"
                        "4. ORDER BY DESC(?count) LIMIT 1 selects the year with the highest count. GROUP_CONCAT handles ties."
                    )
                }
            ),
        ),
    ],
}

# Extra few-shots injected only for COUNT samples.
COUNT_EXTRA_SHOTS: list[PromptMessage] = [
    PromptMessage(
        role="human",
        content=(
            "**Query Type**: COUNT\n"
            "**Question**: How many research papers has Ishimatsu, Jun published?\n"
            "**Entities**: <https://dblp.org/pid/74/7568>\n"
            "**Relations**: <https://dblp.org/rdf/schema#authoredBy>\n"
            "**GOLD SPARQL**: SELECT (COUNT(DISTINCT ?answer) AS ?count) WHERE { "
            "?answer <https://dblp.org/rdf/schema#authoredBy> <https://dblp.org/pid/74/7568> }"
        ),
    ),
    PromptMessage(
        role="ai",
        content=json.dumps(
            {
                "explanation": (
                    "1. Query type: COUNT (simple). Target variable: ?count.\n"
                    "2. ?answer (publication) --authoredBy--> <person>. Publication is subject.\n"
                    "3. COUNT(DISTINCT ?answer) counts all distinct publications. No subquery needed for a simple count."
                )
            }
        ),
    ),
]

# Extra few-shots injected only for SUPERLATIVE+COMPARATIVE samples.
SUPERLATIVE_EXTRA_SHOTS: list[PromptMessage] = [
    # MIN variant
    PromptMessage(
        role="human",
        content=(
            "**Query Type**: SUPERLATIVE+COMPARATIVE\n"
            "**Question**: When was the first paper by Tom Tollenaere published?\n"
            "**Entities**: <https://dblp.org/pid/44/6536>\n"
            "**Relations**: <https://dblp.org/rdf/schema#authoredBy>, <https://dblp.org/rdf/schema#yearOfPublication>\n"
            "**GOLD SPARQL**: SELECT DISTINCT MIN(xsd:integer(?answer)) AS ?answer WHERE { "
            "?x <https://dblp.org/rdf/schema#authoredBy> <https://dblp.org/pid/44/6536> . "
            "?x <https://dblp.org/rdf/schema#yearOfPublication> ?answer }"
        ),
    ),
    PromptMessage(
        role="ai",
        content=json.dumps(
            {
                "explanation": (
                    "1. Query type: SUPERLATIVE+COMPARATIVE. 'First paper' = earliest year = MIN.\n"
                    "2. ?x (publication) --authoredBy--> <person>. ?x --yearOfPublication--> ?answer.\n"
                    "3. MIN(xsd:integer(?answer)) selects the smallest year. xsd:integer cast ensures numeric comparison."
                )
            }
        ),
    ),
    # BIND(IF) variant
    PromptMessage(
        role="human",
        content=(
            "**Query Type**: SUPERLATIVE+COMPARATIVE\n"
            "**Question**: Which one has more number of authors, 'Plastic Waste is Exponentially Filling our Oceans' or 'A Refined Mean Field Approximation'?\n"
            "**Entities**: <https://dblp.org/rec/journals/corr/abs-1809-00798>, <https://dblp.org/rec/conf/sigmetrics/GastH18>\n"
            "**Relations**: <https://dblp.org/rdf/schema#numberOfCreators>\n"
            "**GOLD SPARQL**: SELECT DISTINCT ?answer WHERE { "
            "<https://dblp.org/rec/journals/corr/abs-1809-00798> <https://dblp.org/rdf/schema#numberOfCreators> ?x . "
            "<https://dblp.org/rec/conf/sigmetrics/GastH18> <https://dblp.org/rdf/schema#numberOfCreators> ?y . "
            "BIND(IF(?x > ?y, <https://dblp.org/rec/journals/corr/abs-1809-00798>, <https://dblp.org/rec/conf/sigmetrics/GastH18>) AS ?answer) }"
        ),
    ),
    PromptMessage(
        role="ai",
        content=json.dumps(
            {
                "explanation": (
                    "1. Query type: SUPERLATIVE+COMPARATIVE. Comparing two specific publications.\n"
                    "2. <pub1> --numberOfCreators--> ?x. <pub2> --numberOfCreators--> ?y. Gets author count for each.\n"
                    "3. BIND(IF(?x > ?y, <pub1>, <pub2>) AS ?answer) selects the publication with more authors.\n"
                    "4. BIND(IF) is used because we compare exactly two known entities, not an aggregation over a set."
                )
            }
        ),
    ),
]

# SCHEMAS ---------------------------------------------------------------------
class SyntheticExplanation(BaseModel):
    explanation: str = Field(
        description="The numbered step-by-step reasoning trace that explains how to construct the SPARQL query from the question. Follow the exact format specified in the system prompt."
    )


class EnrichedSample(BaseModel):
    id: str
    explanation: str


class DatasetExplanations(BaseModel):
    samples: list[EnrichedSample] = Field(default_factory=list)


# UTILS -----------------------------------------------------------------------
def _get_few_shot_for_type(query_type: QUERY_TYPE) -> list[PromptMessage]:
    messages: list[PromptMessage] = []

    if query_type in FEW_SHOT_MESSAGES:
        messages.extend(FEW_SHOT_MESSAGES[query_type])

    if query_type == "SUPERLATIVE+COMPARATIVE":
        messages.extend(SUPERLATIVE_EXTRA_SHOTS)
    elif query_type == "COUNT":
        messages.extend(COUNT_EXTRA_SHOTS)

    related: dict[QUERY_TYPE, QUERY_TYPE] = {
        "NEGATION": "BOOLEAN",
        "DOUBLE_NEGATION": "NEGATION",
    }
    if query_type in related:
        related_type = related[query_type]
        if related_type in FEW_SHOT_MESSAGES:
            messages.extend(FEW_SHOT_MESSAGES[related_type])

    return messages


# MAIN ------------------------------------------------------------------------
def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)

    llm_service = LLMService(
        LLMServiceConfig(
            temperature=1.0,
            max_tokens=None,
            backend=GoogleBackendConfig(
                model_name="gemini-3-flash-preview",
                thinking_level="high",
            ),
        )
    )
    dataset_service = DblpQuadService(DblpQuadServiceConfig())
    dataset = dataset_service.load("train", "questions")

    output_file = PROJECT_ROOT / _EXPLANATIONS_PATH
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Resume support
    results = DatasetExplanations()
    processed_ids: set[str] = set()

    if output_file.exists():
        existing = DatasetExplanations.model_validate_json(
            output_file.read_text()
        )
        results.samples = existing.samples
        processed_ids = {s.id for s in existing.samples}
        print(f"Resumed: {len(processed_ids)} samples already processed.")

    total = len(dataset.questions)
    errors = 0

    print(
        f"Starting generation for {total} questions "
        f"({len(processed_ids)} already done)..."
    )

    for sample in dataset.questions:
        if sample.id in processed_ids:
            continue

        entities_str = (
            ", ".join(sample.entities) if sample.entities else "None"
        )
        relations_str = (
            ", ".join(sample.relations) if sample.relations else "None"
        )

        human_content = (
            f"**Query Type**: {sample.query_type}\n"
            f"**Question**: {sample.question.string}\n"
            f"**Entities**: {entities_str}\n"
            f"**Relations**: {relations_str}\n"
            f"**GOLD SPARQL**: {sample.query.sparql}"
        )

        few_shot = _get_few_shot_for_type(sample.query_type)

        prompt_messages = (
            [PromptMessage(role="system", content=SYSTEM_PROMPT)]
            + few_shot
            + [PromptMessage(role="human", content=human_content)]
        )

        try:
            llm_output: SyntheticExplanation = (
                llm_service.invoke_with_structured_output(
                    prompt_messages=prompt_messages,
                    output_schema=SyntheticExplanation,
                )
            )

            results.samples.append(
                EnrichedSample(
                    id=sample.id, explanation=llm_output.explanation
                )
            )
            processed_ids.add(sample.id)

        except Exception as e:
            errors += 1
            logger.error(f"Failed on sample {sample.id}: {e}")
            continue

        # Progress + periodic save
        done = len(processed_ids)
        if done % 50 == 0:
            print(f"Progress: {done}/{total} ({errors} errors)")
            output_file.write_text(
                results.model_dump_json(indent=2), encoding="utf-8"
            )

    # Final save
    output_file.write_text(
        results.model_dump_json(indent=2), encoding="utf-8"
    )

    print(
        f"Done! {len(results.samples)} explanations saved to {output_file}"
    )
    if errors:
        print(f"Warning: {errors} samples failed.")


if __name__ == "__main__":
    main()
