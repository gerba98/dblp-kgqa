import logging
import socket
import subprocess
import time
import urllib.error
import urllib.request
from typing import Literal

from SPARQLWrapper import JSON, SPARQLWrapper

from dblp_kgqa.modules.query_executor.base import (
    BaseQueryExecutor,
    BaseQueryExecutorConfig,
)
from dblp_kgqa.modules.schemas import PipelineOutput, SparqlResult

logger = logging.getLogger(__name__)

class EndpointQueryExecutorConfig(BaseQueryExecutorConfig):
    strategy: Literal["EndpointQueryExecutor"] = "EndpointQueryExecutor"
    endpoint: str = "https://sparql.dblp.org/sparql"
    timeout: int = 20
    local_docker: bool = False
    docker_container_name: str = "dblp-dump-virtuoso-1"
    docker_ready_timeout: int = 60


class EndpointQueryExecutor(BaseQueryExecutor):
    def __init__(self, config: EndpointQueryExecutorConfig):
        self.config = config
        self.sparql_wrapper = SPARQLWrapper(config.endpoint)
        self.sparql_wrapper.setReturnFormat(JSON)
        self.sparql_wrapper.setTimeout(config.timeout)

    def __call__(self, pipeline_output: PipelineOutput) -> SparqlResult | None:
        query = pipeline_output.generated_query.query
        raw_result = self._execute_query(query)
        if raw_result is None:
            return None
        result = SparqlResult.model_validate(raw_result)
        logger.info(f"DONE - SPARQL result: {result.model_dump_json()}")
        return result

    def _execute_query(self, query):
        try:
            self.sparql_wrapper.setQuery(query)
            result = self.sparql_wrapper.queryAndConvert()
            return result
        except Exception as e:
            logger.error(
                "XXXX Query execution failed - "
                f"Failed query: {query} - "
                f"Error: {type(e).__name__} - {str(e)}"
            )
            if self.config.local_docker and (
                isinstance(e, (TimeoutError, socket.timeout))
                or "timed out" in str(e).lower()
            ):
                self._restart_local_docker()
            return None

    def _restart_local_docker(self):
        name = self.config.docker_container_name
        logger.warning(
            f"Timeout detected, restarting docker container {name!r}"
        )
        subprocess.run(
            ["docker", "restart", name], check=True, timeout=30
        )
        deadline = time.monotonic() + self.config.docker_ready_timeout
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(
                    self.config.endpoint, timeout=3
                ) as r:
                    if r.status == 200:
                        logger.info(f"Container {name!r} ready")
                        return
            except (
                urllib.error.URLError,
                urllib.error.HTTPError,
                TimeoutError,
            ):
                pass
            time.sleep(2)
        raise RuntimeError(
            f"Container {name!r} did not become ready within "
            f"{self.config.docker_ready_timeout}s"
        )
