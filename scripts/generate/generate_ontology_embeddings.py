import logging
import sys

from pydantic import BaseModel, Field

from dblp_kgqa import PROJECT_ROOT
from dblp_kgqa.services.embedding import (
    EmbeddingService,
    EmbeddingServiceConfig,
)
from dblp_kgqa.services.neo4j import Neo4jService, Neo4jServiceConfig

logger = logging.getLogger(__name__)

# CONFIG ----------------------------------------------------------------------

SCHEMA_VERSION = "current"
# SCHEMA_VERSION = "dblp_quad"
TASK_TYPE = "RETRIEVAL_DOCUMENT"
EMBEDDING_TEXT_FORMAT = "{name}: {comment}"
EXCLUDED_PREDICATES: set[str] = {"authorOf", "creatorOf", "editorOf"}
# EXCLUDED_PREDICATES: set[str] = set()

# SCHEMAS ---------------------------------------------------------------------
class PropertyEmbedding(BaseModel):
    uri: str
    name: str
    comment: str
    embedding_text: str
    embedding: list[float]


class OntologyEmbeddings(BaseModel):
    properties: list[PropertyEmbedding] = Field(default_factory=list)

# UTILS -----------------------------------------------------------------------
def _schema_path(schema_version: str) -> str:
    return f"data/dblp_schema/schema_{schema_version}.ttl"


def _ontology_embeddings_path(schema_version: str, model_name: str) -> str:
    model_slug = model_name.replace("/", "_")
    return (
        f"data/dblp_schema/"
        f"ontology_embeddings_{schema_version}_{model_slug}.json"
    )

# MAIN ------------------------------------------------------------------------
def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)

    neo4j_service = Neo4jService(Neo4jServiceConfig())
    embedding_service = EmbeddingService(
        EmbeddingServiceConfig(
            model_name="gemini-embedding-001",
            task_type=TASK_TYPE,
        )
    )

    # Import ontology into Neo4j via n10s
    neo4j_service._import_dblp_ontology(_schema_path(SCHEMA_VERSION))
    print("Ontology imported into Neo4j.")

    # Query all Relationship nodes with comments + domain/range
    records = neo4j_service.execute_query("""//cypher
        MATCH (p:Relationship)
        WHERE p.comment IS NOT NULL
        OPTIONAL MATCH (p)-[:DOMAIN]->(d)
        OPTIONAL MATCH (p)-[:RANGE]->(r)
        WITH p,
            head(collect(DISTINCT d.name)) AS domain,
            head(collect(DISTINCT r.name)) AS range
        RETURN p.uri AS uri,
                p.name AS name,
                p.comment AS comment,
                coalesce(domain, 'Entity') AS domain,
                coalesce(range, 'literal') AS range
        ORDER BY p.uri
    """)

    if not records:
        print("No ontology properties found!")
        return

    print(f"Found {len(records)} properties with comments.")

    if EXCLUDED_PREDICATES:
        before = len(records)
        records = [r for r in records if r["name"] not in EXCLUDED_PREDICATES]
        print(
            f"Excluded {before - len(records)} predicates "
            f"({sorted(EXCLUDED_PREDICATES)}); "
            f"{len(records)} remain."
        )

    # Build embedding texts from the configured format
    embedding_texts = []
    for r in records:
        text = EMBEDDING_TEXT_FORMAT.format(**r)
        embedding_texts.append(text)
        print(f"  {text}")

    # Embed texts in a single batch
    embeddings = embedding_service.embed_batch(embedding_texts)

    print(f"Generated {len(embeddings)} embeddings.")

    output_file = PROJECT_ROOT / _ontology_embeddings_path(
        SCHEMA_VERSION, embedding_service.config.model_name
    )
    output_file.parent.mkdir(parents=True, exist_ok=True)

    results = OntologyEmbeddings(
        properties=[
            PropertyEmbedding(
                uri=r["uri"],
                name=r["name"],
                comment=r["comment"],
                embedding_text=emb_text,
                embedding=emb,
            )
            for r, emb_text, emb in zip(
                records, embedding_texts, embeddings, strict=True
            )
        ]
    )

    output_file.write_text(results.model_dump_json(indent=2), encoding="utf-8")

    print(
        f"Done! {len(results.properties)} embeddings "
        f"saved to {output_file}"
    )


if __name__ == "__main__":
    main()
