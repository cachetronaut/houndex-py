from __future__ import annotations

from typing import Any

from houndex_core.providers import ScrapedPage
from houndex_core.schemas import ExtractedClaim
from pydantic import BaseModel, Field


class VerdictResponse(BaseModel):
    trace_resolution: float
    envelope_validity: float
    determinism: float | None
    total: float
    passed: bool
    notes: list[str]


class AskRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=10, ge=1, le=100)


class AskResponse(BaseModel):
    envelope: dict[str, Any]
    verdict: VerdictResponse


class IngestPage(BaseModel):
    source_url: str = Field(min_length=1)
    title: str = ""
    text: str = Field(min_length=1)
    claims: list[ExtractedClaim] = Field(default_factory=list)

    def scraped_page(self) -> ScrapedPage:
        return ScrapedPage(source_url=self.source_url, title=self.title, text=self.text)


class IngestRequest(BaseModel):
    subject: str = Field(min_length=1)
    signal: str | None = None
    pages: list[IngestPage] = Field(min_length=1)
