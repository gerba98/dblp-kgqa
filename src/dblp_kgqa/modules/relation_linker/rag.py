import json
import logging
from typing import Literal

from pydantic import BaseModel

from dblp_kgqa import SchemaVersion
from dblp_kgqa.modules.relation_linker.base import (
    BaseRelationLinker,
    BaseRelationLinkerConfig,
)
from dblp_kgqa.modules.schemas import (
    LinkedRelation,
    PipelineOutput,
)
from dblp_kgqa.services.embedding import EmbeddingService
from dblp_kgqa.services.neo4j import Neo4jService

logger = logging.getLogger(__name__)

# SCHEMAS ---------------------------------------------------------------------

class PropertyEntry(BaseModel):
    IRI: str
    description: str
    domain: str
    range: str


class PropertyEntryMinimal(BaseModel):
    IRI: str
    description: str

# UTILS -----------------------------------------------------------------------

def _schema_path(schema_version: SchemaVersion) -> str:
    return f"data/dblp_schema/schema_{schema_version}.ttl"


def _ontology_embeddings_path(
    schema_version: SchemaVersion, model_name: str
) -> str:
    model_slug = model_name.replace("/", "_")
    return (
        f"data/dblp_schema/"
        f"ontology_embeddings_{schema_version}_{model_slug}.json"
    )

# MODULE ----------------------------------------------------------------------

class RAGRelationLinkerConfig(BaseRelationLinkerConfig):
    strategy: Literal["RagRelationLinker"] = "RagRelationLinker"
    neo4j_service_name: str = "local_neo4j"
    embedding_service_name: str = "google_embedding_rq"
    num_properties: int = 10
    schema_version: SchemaVersion = "current"
    include_domain_range: bool = True

RELATIONS_PROMPT_CONTEXT = (
    "The 'relations' field in the user message lists DBLP schema predicate "
    "URIs retrieved by semantic similarity. Each entry includes 'IRI', "
    "'description', 'domain', 'range' — read descriptions carefully to "
    "pick the right predicate. Domain and range indicate which entity "
    "types can be subject and object respectively. Use ONLY these "
    "predicates in your triple patterns. Never invent predicates."
)

RELATIONS_PROMPT_CONTEXT_MINIMAL = (
    "The 'relations' field in the user message lists DBLP schema predicate "
    "URIs retrieved by semantic similarity. Each entry includes 'IRI' and "
    "'description'. Read descriptions carefully to pick the right "
    "predicate. Use ONLY these predicates in your triple patterns. Never "
    "invent predicates."
)

class RAGRelationLinker(BaseRelationLinker):
    config: RAGRelationLinkerConfig

    def __init__(
        self,
        config: RAGRelationLinkerConfig,
        neo4j_service: Neo4jService,
        embedding_service: EmbeddingService,
    ):
        self.config = config
        self.neo4j_service = neo4j_service
        self.embedding_service = embedding_service

        neo4j_service.load_dblp_ontology(
            schema_path=_schema_path(config.schema_version),
            ontology_embeddings_file=_ontology_embeddings_path(
                config.schema_version,
                embedding_service.config.model_name,
            ),
        )

    def __call__(self, pipeline_output: PipelineOutput) -> LinkedRelation:
        schema_dict = self._retrieve_properties(pipeline_output.question)

        description = (
            RELATIONS_PROMPT_CONTEXT
            if self.config.include_domain_range
            else RELATIONS_PROMPT_CONTEXT_MINIMAL
        )
        result = LinkedRelation(
            description=description,
            schema_context=[json.dumps(schema_dict, indent=4)],
        )
        logger.info(f"DONE - Linked relation: {json.dumps(schema_dict)}")
        return result

    def _retrieve_properties(
        self, question: str
    ) -> dict[str, dict[str, str]]:
        embedding = self.embedding_service.embed(question)
        results = self.neo4j_service.search_ontology_properties(
            embedding=embedding,
            k=self.config.num_properties,
        )
        scores = [
            (r["result"]["name"], f'{r["result"]["vec_score"]:.4f}')
            for r in results
        ]
        logger.debug(
            f">>>> Vector search returned {len(results)} results: {scores}"
        )

        if self.config.include_domain_range:
            return {
                r["result"]["name"]: PropertyEntry(
                    IRI=r["result"]["uri"],
                    description=r["result"]["comment"],
                    domain=r["result"]["domain"] or "Entity",
                    range=r["result"]["range"] or "literal",
                ).model_dump()
                for r in results
            }

        return {
            r["result"]["name"]: PropertyEntryMinimal(
                IRI=r["result"]["uri"],
                description=r["result"]["comment"],
            ).model_dump()
            for r in results
        }

