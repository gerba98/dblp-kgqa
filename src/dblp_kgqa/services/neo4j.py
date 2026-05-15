import logging
from typing import Any, Literal, LiteralString, cast

from neo4j import GraphDatabase

from dblp_kgqa import settings
from dblp_kgqa.services.base import BaseService, BaseServiceConfig

logger = logging.getLogger(__name__)


class Neo4jServiceConfig(BaseServiceConfig):
    type: Literal["Neo4j"] = "Neo4j"
    uri: str = "bolt://neo4j:7687"


class Neo4jService(BaseService):
    def __init__(self, config: Neo4jServiceConfig):
        self.config = config
        self._init_driver()
        self._clear_neo4j()

    def _init_driver(self):
        self.driver = GraphDatabase.driver(
            self.config.uri,
            auth=(
                settings.neo4j_username,
                settings.neo4j_password.get_secret_value(),
            ),
        )
        try:
            self.driver.verify_connectivity()
            logger.debug(">>>> connected to Neo4j")
        except Exception:
            logger.critical("XXXX Unable to connect to Neo4j")
            self.driver.close()
            raise

    def execute_query(
        self,
        cypher: LiteralString,
        parameters: dict[str, Any] | None = None,
    ):
        parameters = parameters or {}
        records, _, _ = self.driver.execute_query(
            cypher, parameters_=parameters
        )
        return [record.data() for record in records]

    def _clear_neo4j(self):
        cypher = """//cypher
            MATCH (n)
            CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS
        """
        with self.driver.session() as session:
            session.run(cypher).consume()

        self.execute_query("""//cypher
            CALL apoc.schema.assert({}, {}, true);
        """)
        self.execute_query("""//cypher
            CALL n10s.graphconfig.drop();
        """)
        logger.debug(">>>> Neo4j db cleared")

    def import_json(
        self,
        file_path: str,
        cypher: str,
        items_field: str | None = None,
    ):
        # `file_path` is relative to Neo4j's import dir.
        json_url = f"file:///{file_path}"
        items_expr = f", '{items_field}'" if items_field else ""

        full_query = f"""//cypher
            CALL apoc.load.json($json_url{items_expr}) YIELD value AS row
            {cypher}
        """
        self.execute_query(
            cast(LiteralString, full_query), {"json_url": json_url}
        )
        logger.debug(f">>>> json Imported from {file_path}")

    def similarity_search(
        self,
        embedding: list[float],
        cypher: str,
        *,
        k: int = 5,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        all_params: dict[str, Any] = {
            "embedding": embedding,
            "k": k,
            **(params or {}),
        }
        return self.execute_query(cast(LiteralString, cypher), all_params)

    def _import_dblp_quad(self, questions_file: str):
        self.import_json(
            file_path=questions_file,
            items_field="questions",
            cypher="""
                MERGE (qt:QueryType {name: row.query_type})
                MERGE (q:QuestionSample {id: row.id})
                SET q.sparql = row.query.sparql,
                    q.template_id = row.template_id,
                    q.entities = row.entities,
                    q.relations = row.relations,
                    q.temporal = row.temporal,
                    q.held_out = row.held_out
                MERGE (q)-[:HAS_TYPE]->(qt)

                MERGE (orig:Question {text: row.question.string})
                MERGE (orig)-[:IS_ORIGINAL_OF]->(q)

                MERGE (para:Question {text: row.paraphrased_question.string})
                MERGE (para)-[:IS_PARAPHRASED_OF]->(q)
            """,
        )
        logger.debug(">>>> DBLP QuAD questions imported")

    def _import_dblp_quad_embeddings(self, embeddings_file: str):
        self.import_json(
            file_path=embeddings_file,
            items_field="samples",
            cypher="""
                MATCH (q:QuestionSample {id: row.id})

                WITH q, row
                MATCH (orig:Question)-[:IS_ORIGINAL_OF]->(q)
                CALL db.create.setNodeVectorProperty(
                    orig, 'embedding', row.question_embedding
                )

                WITH q, row
                MATCH (para:Question)-[:IS_PARAPHRASED_OF]->(q)
                CALL db.create.setNodeVectorProperty(
                    para, 'embedding', row.paraphrased_question_embedding
                )
            """,
        )
        logger.debug(">>>> DBLP QuAD embeddings imported")

    def _import_dblp_quad_explanations(self, explanations_file: str):
        self.import_json(
            file_path=explanations_file,
            items_field="samples",
            cypher="""
                MATCH (q:QuestionSample {id: row.id})
                SET q.explanation = row.explanation
            """,
        )
        logger.debug(">>>> DBLP QuAD explanations imported")

    def load_dblp_quad(
        self,
        questions_file: str,
        questions_embeddings_file: str,
        explanations_file: str,
    ):
        self._import_dblp_quad(questions_file)
        self._import_dblp_quad_embeddings(questions_embeddings_file)
        self._import_dblp_quad_explanations(explanations_file)

    def search_dblp_quad(
        self,
        embedding: list[float],
        query_type: str | None = None,
        k: int = 5,
    ) -> list[dict[str, Any]]:
        cypher = """//cypher
            MATCH (s:QuestionSample)
                <-[:IS_ORIGINAL_OF|IS_PARAPHRASED_OF]-(q:Question)
            WHERE $query_type IS NULL OR EXISTS {
                (s)-[:HAS_TYPE]->(:QueryType {name: $query_type})
            }
            WITH s, q,
                vector.similarity.cosine(
                    q.embedding, $embedding
                ) AS score
            ORDER BY score DESC
            WITH s, collect(q)[0] AS bestQ, max(score) AS score
            ORDER BY score DESC
            LIMIT $k
            MATCH (s)-[:HAS_TYPE]->(qt:QueryType)
            RETURN {
                id: s.id,
                query_type: qt.name,
                question: bestQ.text,
                sparql: s.sparql,
                entities: s.entities,
                relations: s.relations,
                explanation: s.explanation,
                score: score
            } AS result
        """
        return self.similarity_search(
            embedding=embedding,
            cypher=cypher,
            k=k,
            params={"query_type": query_type},
        )

    def _import_dblp_ontology(self, schema_path: str):
        self.execute_query("""//cypher
            CREATE CONSTRAINT n10s_unique_uri IF NOT EXISTS
            FOR (r:Resource) REQUIRE r.uri IS UNIQUE
        """)
        self.execute_query("""//cypher
            CALL n10s.graphconfig.init({handleVocabUris: "IGNORE"})
        """)
        schema_url = "file:///var/lib/neo4j/import/" + schema_path
        self.execute_query(
            "CALL n10s.onto.import.fetch($url, 'Turtle')",
            {"url": schema_url},
        )
        logger.debug(">>>> DBLP ontology imported")

    def _import_ontology_embeddings(self, embeddings_file: str):
        self.import_json(
            file_path=embeddings_file,
            items_field="properties",
            cypher="""
                MATCH (p) WHERE p.uri = row.uri
                CALL db.create.setNodeVectorProperty(
                    p, 'embedding', row.embedding
                )
            """,
        )
        logger.debug(">>>> Ontology embeddings imported")

    def load_dblp_ontology(
        self,
        schema_path: str,
        ontology_embeddings_file: str,
    ):
        self._import_dblp_ontology(schema_path)
        self._import_ontology_embeddings(ontology_embeddings_file)
        logger.debug(">>>> DBLP ontology loaded")

    def search_ontology_properties(
        self,
        embedding: list[float],
        k: int = 15,
    ) -> list[dict[str, Any]]:
        cypher = """//cypher
            MATCH (p:Relationship)
            WHERE p.embedding IS NOT NULL
            WITH p,
                vector.similarity.cosine(
                    p.embedding, $embedding
                ) AS vec_score
            ORDER BY vec_score DESC
            LIMIT $k
            OPTIONAL MATCH (p)-[:DOMAIN]->(d)
            OPTIONAL MATCH (p)-[:RANGE]->(r)
            WITH p, vec_score,
                head(collect(DISTINCT d.name)) AS domain,
                head(collect(DISTINCT r.name)) AS range
            RETURN {
                name: p.name,
                uri: p.uri,
                comment: p.comment,
                domain: domain,
                range: range,
                vec_score: vec_score
            } AS result
        """
        return self.similarity_search(
            embedding=embedding,
            cypher=cypher,
            k=k,
        )
