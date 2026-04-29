from __future__ import annotations

import re
from enum import StrEnum
from typing import Annotated

from pydantic import Field, conlist, field_validator, model_validator

from schemas.base import DocId, NonEmptyStr, OpsSuiteBaseModel, ShortStr, UtcDateTime, utcnow


class QueryRoute(StrEnum):
    FACT_ONLY = "fact_only"
    FEE_ONLY = "fee_only"
    BOTH = "both"


class DocType(StrEnum):
    FACTSHEET = "factsheet"
    FEE = "fee"


class RAGQuery(OpsSuiteBaseModel):
    query: NonEmptyStr
    request_id: ShortStr
    top_k: Annotated[int, Field(ge=1, le=50, default=10)] = 10
    rerank_k: Annotated[int, Field(ge=1, le=20, default=3)] = 3

    @model_validator(mode="after")
    def rerank_le_top_k(self) -> RAGQuery:
        if self.rerank_k > self.top_k:
            raise ValueError(
                f"rerank_k ({self.rerank_k}) must be <= top_k ({self.top_k}). "
                "Decrease rerank_k or increase top_k."
            )
        return self


class Citation(OpsSuiteBaseModel):
    doc_id: DocId
    chunk_index: Annotated[int, Field(ge=0)]
    score: Annotated[float, Field(ge=0.0, le=1.0)]
    doc_type: DocType
    section: ShortStr


_SOURCE_TAG_RE = re.compile(r"\[source:[A-Za-z0-9_\-]{3,64}\]")


class Bullet(OpsSuiteBaseModel):
    text: Annotated[str, Field(min_length=10, max_length=500)]
    sources: conlist(Citation, min_length=1, max_length=5)  # type: ignore[valid-type]

    @field_validator("text")
    @classmethod
    def must_contain_source_tag(cls, v: str) -> str:
        if not _SOURCE_TAG_RE.search(v):
            raise ValueError(
                "Bullet text must contain at least one inline citation tag in the format "
                "[source:<doc_id>] (e.g. [source:axis_elss]). Add a citation tag to the text."
            )
        return v


class RAGAnswer(OpsSuiteBaseModel):
    query: NonEmptyStr
    route: QueryRoute
    bullets: conlist(Bullet, min_length=3, max_length=3)  # type: ignore[valid-type]
    retrieved_chunks: conlist(Citation, min_length=1, max_length=20)  # type: ignore[valid-type]
    generated_at: UtcDateTime = Field(default_factory=utcnow)
    model_name: ShortStr
    request_id: ShortStr

    @model_validator(mode="after")
    def all_bullet_sources_in_retrieved(self) -> RAGAnswer:
        retrieved_ids = {c.doc_id for c in self.retrieved_chunks}
        missing: set[str] = set()
        for bullet in self.bullets:
            for citation in bullet.sources:
                if citation.doc_id not in retrieved_ids:
                    missing.add(citation.doc_id)
        if missing:
            raise ValueError(
                "Bullet citations reference doc_id(s) not in retrieved_chunks: "
                f"{sorted(missing)}. All cited doc_ids must appear in retrieved_chunks "
                "to prevent hallucinated citations."
            )
        return self
