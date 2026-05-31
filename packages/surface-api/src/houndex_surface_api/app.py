from __future__ import annotations

import json
from collections.abc import AsyncIterator, Sequence

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from houndex_cli import VerifyFile
from houndex_cli import commands as cli_commands
from houndex_cli.engine import build_claim
from houndex_connectors import IngestConnectorOptions, SourceDraft, ingest_connector
from houndex_core.providers import ScrapedPage
from houndex_core.schemas import ExtractedClaim, Source
from houndex_core.storage import (
    EnsureTenantInput,
    UpsertClaimInput,
    UpsertSourceInput,
)
from houndex_core.tenant import TenantContext
from houndex_pipeline import (
    ExtractedClaimWithContext,
    ExtractInput,
    ExtractionOutcome,
    IngestionInput,
    ProcessDeps,
    SinkResult,
    SourceTierClassifier,
)

from .deps import ApiDeps, build_api_deps
from .schemas import AskRequest, AskResponse, IngestPage, IngestRequest, VerdictResponse


class PageConnector:
    name = "pages"

    def __init__(self, pages: Sequence[IngestPage]) -> None:
        self._pages = pages

    async def pages(self) -> AsyncIterator[ScrapedPage]:
        for page in self._pages:
            yield page.scraped_page()


def create_app(deps: ApiDeps | None = None) -> FastAPI:
    app = FastAPI(title="Houndex Surface API", version="0.1.0")

    async def get_deps(request: Request) -> ApiDeps:
        if deps is not None:
            return deps
        cached = getattr(request.app.state, "houndex_deps", None)
        if cached is None:
            cached = await build_api_deps()
            request.app.state.houndex_deps = cached
        return cached

    async def tenant_header(x_houndex_tenant: str | None = Header(default=None)) -> str:
        if x_houndex_tenant is None or not x_houndex_tenant.strip():
            raise HTTPException(status_code=400, detail="X-Houndex-Tenant header is required")
        return x_houndex_tenant

    @app.post("/verify", response_model=VerdictResponse)
    async def verify(
        request: VerifyFile,
        tenant_id: str = Depends(tenant_header),  # noqa: B008
        api_deps: ApiDeps = Depends(get_deps),  # noqa: B008
    ) -> dict[str, object]:
        command_deps = api_deps.command_deps(tenant_id)
        result = await cli_commands.verify(
            command_deps,
            envelope=request.envelope,
            claim_ids=request.claim_ids,
            as_json=True,
        )
        return json.loads(result.output)

    @app.post("/ask", response_model=AskResponse)
    async def ask(
        request: AskRequest,
        tenant_id: str = Depends(tenant_header),  # noqa: B008
        api_deps: ApiDeps = Depends(get_deps),  # noqa: B008
    ) -> dict[str, object]:
        command_deps = api_deps.command_deps(tenant_id)
        result = await cli_commands.ask(
            command_deps,
            query=request.query,
            limit=request.limit,
            as_json=True,
        )
        return json.loads(result.output)

    @app.post("/ingest")
    async def ingest(
        request: IngestRequest,
        tenant_id: str = Depends(tenant_header),  # noqa: B008
        api_deps: ApiDeps = Depends(get_deps),  # noqa: B008
    ) -> dict[str, object]:
        command_deps = api_deps.command_deps(tenant_id)
        tenant = command_deps.config.tenant_context()
        await api_deps.adapter.ensure_tenant(EnsureTenantInput(tenant=tenant))

        result = await ingest_connector(
            PageConnector(request.pages),
            IngestionInput(subject=request.subject, signal=request.signal),
            ProcessDeps(
                classifier=SourceTierClassifier(),
                extract=_extractor_for(request.pages),
                sink=_sink_for(api_deps, tenant_id),
                embed=None,
            ),
            IngestConnectorOptions(
                now=command_deps.now,
                upsert_source=_source_upserter_for(api_deps, tenant),
            ),
        )
        return {
            "pages_scraped": result.pages_scraped,
            "pages_failed": result.pages_failed,
            "claims_extracted": result.claims_extracted,
            "claims_dropped": result.claims_dropped,
            "claims_created": result.claims_created,
            "claims_deduped": result.claims_deduped,
            "scraped_hashes": result.scraped_hashes,
        }

    return app


def _extractor_for(pages: Sequence[IngestPage]):
    claims_by_url = {page.source_url: page.claims for page in pages}

    async def extract(input: ExtractInput) -> ExtractionOutcome:
        return ExtractionOutcome(
            kept=[
                ExtractedClaimWithContext(
                    claim=claim,
                    subject=input.subject,
                    source_url=input.source_url,
                    source_tier=input.source_tier,
                )
                for claim in claims_by_url.get(input.source_url, [])
            ],
            dropped=[],
        )

    return extract


def _sink_for(api_deps: ApiDeps, tenant_id: str):
    async def sink(
        claim: ExtractedClaimWithContext, embedding: Sequence[float] | None
    ) -> SinkResult:
        tenant = api_deps.command_deps(tenant_id).config.tenant_context()
        stored = build_claim(
            tenant.tenant_id,
            {
                **_claim_content(claim.claim),
                "subject": claim.subject,
                "source_url": claim.source_url,
                "source_tier": claim.source_tier,
                "extracted_at": api_deps.now(),
            },
        )
        result = await api_deps.adapter.upsert_claim(
            UpsertClaimInput(tenant=tenant, claim=stored, embedding=embedding)
        )
        return SinkResult(claim_id=result.id, created=result.created)

    return sink


def _source_upserter_for(api_deps: ApiDeps, tenant: TenantContext):
    async def upsert_source(draft: SourceDraft) -> None:
        await api_deps.adapter.upsert_source(
            UpsertSourceInput(
                tenant=tenant,
                source=Source(
                    tenant_id=tenant.tenant_id,
                    url=draft.url,
                    title=draft.title,
                    domain=draft.domain,
                    tier=draft.tier,
                    fetched_at=draft.fetched_at,
                ),
            )
        )

    return upsert_source


def _claim_content(claim: ExtractedClaim) -> dict[str, object]:
    return {
        "category": claim.category,
        "polarity": claim.polarity,
        "scope": claim.scope,
        "claim_text": claim.claim_text,
        "evidence_text": claim.evidence_text,
        "confidence": claim.confidence,
    }
