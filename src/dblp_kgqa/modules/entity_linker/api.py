import difflib
import html
import logging
import re
from typing import Literal

import requests
from pydantic import BaseModel, Field, field_validator

from dblp_kgqa.modules.entity_linker.base import (
    BaseEntityLinker,
    BaseEntityLinkerConfig,
)
from dblp_kgqa.modules.schemas import (
    LinkedEntities,
    LinkedEntity,
    PipelineOutput,
)

logger = logging.getLogger(__name__)

ENTITIES_PROMPT_CONTEXT = (
    "The 'entities' field in the user message lists entities linked from "
    "the question, each with a type (person/publication/venue) and a URI "
    "(possibly empty). Use these URIs verbatim in your SPARQL. Venue "
    "handling is governed by RULE 4."
)

_LUCENE_SPECIAL_RE = re.compile(r'[+!(){}[\]^"~*?:\\/]')
_API_TYPE_BY_ENTITY = {
    "person": ("author", "author"),
    "publication": ("publ", "title"),
    "venue": ("venue", "venue"),
}


class _DblpHitInfo(BaseModel):
    author: str | None = None
    title: str | None = None
    venue: str | list[str] | None = None
    url: str | None = None
    type: str | None = None

    @field_validator("author", "title", "venue", mode="before")
    @classmethod
    def _unescape(cls, v):
        if isinstance(v, list):
            return [html.unescape(s) if isinstance(s, str) else s for s in v]
        return html.unescape(v) if isinstance(v, str) else v


class _DblpHit(BaseModel):
    info: _DblpHitInfo


class _DblpHits(BaseModel):
    hit: list[_DblpHit] = Field(default_factory=list)

    @field_validator("hit", mode="before")
    @classmethod
    def _normalize(cls, v):
        return [v] if isinstance(v, dict) else v


class _DblpResponse(BaseModel):
    result: dict

    @property
    def hits(self) -> list[_DblpHit]:
        return _DblpHits.model_validate(self.result.get("hits", {})).hit


class ApiEntityLinkerConfig(BaseEntityLinkerConfig):
    strategy: Literal["ApiEntityLinker"] = "ApiEntityLinker"
    api_host: str = "https://dblp.org"
    # Mirrors: "https://dblp.uni-trier.de" | "https://dblp.dagstuhl.de"
    difflib_cutoff: float = 0.3


class ApiEntityLinker(BaseEntityLinker):
    def __init__(self, config: ApiEntityLinkerConfig):
        self.config = config
        self._session = requests.Session()
        self._session.headers["User-Agent"] = (
            "ThesisProject/1.1 "
            "(KGQA research; mailto:l.gerbasi@studenti.unisa.it)"
        )

    def __call__(self, pipeline_output: PipelineOutput) -> LinkedEntities:
        result = LinkedEntities(description=ENTITIES_PROMPT_CONTEXT)
        for entity in pipeline_output.extracted_info.named_entities:
            uri = self._link_entity(entity.name, entity.type)
            if uri:
                uri = f"<{uri}>"
            result.linked_entities.append(
                LinkedEntity(name=entity.name, uri=uri, type=entity.type)
            )
        logger.info(f"Done - Linked entities: {result.model_dump_json()}")
        return result

    def _search_dblp(self, query: str, api_type: str) -> list[_DblpHit] | None:
        query = _LUCENE_SPECIAL_RE.sub("", query).replace("-", " ")
        url = f"{self.config.api_host}/search/{api_type}/api"
        try:
            response = self._session.get(
                url,
                params={"q": query, "h": 30, "format": "json"},
                timeout=30,
            )
            response.raise_for_status()
            return _DblpResponse.model_validate(response.json()).hits
        except Exception as e:
            logger.warning(
                f"!!!! API error for ({api_type}, {query}): "
                f"{type(e).__name__}: {e}"
            )
            return None

    def _link_entity(self, entity: str, entity_type: str) -> str:
        api_type, info_field = _API_TYPE_BY_ENTITY[entity_type]
        hits = self._search_dblp(entity, api_type)
        if hits is None:
            return ""

        candidates: dict[str, str] = {}
        for hit in hits:
            value = getattr(hit.info, info_field)
            url = hit.info.url
            if value and url and value not in candidates:
                candidates[value] = url

        matches = difflib.get_close_matches(
            entity, candidates.keys(), n=1, cutoff=self.config.difflib_cutoff
        )
        if matches:
            uri = candidates[matches[0]]
            logger.debug(
                f">>>> ENTITY LINKED: ({entity_type}, {entity}) --> {uri}"
            )
            return uri

        logger.warning(f"!!!! ENTITY NOT LINKED: ({entity_type}, {entity})")
        return ""
