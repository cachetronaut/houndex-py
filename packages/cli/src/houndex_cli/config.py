"""CLI configuration: ``houndex.config.json``. Declares which storage adapter to
talk to plus tenant + embedding settings. Secrets (Supabase key, Convex URL) are
NEVER stored here — they come from environment variables — so the file is safe to
commit. Field aliases keep the on-disk format identical to the TypeScript CLI.
"""

from __future__ import annotations

from typing import Any, Literal

from houndex_core.tenant import TenantContext, TenantRole
from pydantic import BaseModel, ConfigDict, Field

CONFIG_FILENAME = "houndex.config.json"

AdapterName = Literal["local", "supabase", "convex"]


class TenantConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tenant_id: str = Field(default="default", alias="tenantId")
    user_id: str = Field(default="cli", alias="userId")
    role: TenantRole = TenantRole.ADMIN


class EmbeddingConfig(BaseModel):
    provider: Literal["synthetic"] = "synthetic"
    dimensions: int = Field(default=1536, gt=0)


class HoundexConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    adapter: AdapterName = "local"
    tenant: TenantConfig = Field(default_factory=TenantConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)

    def tenant_context(self) -> TenantContext:
        return TenantContext(
            tenant_id=self.tenant.tenant_id,
            user_id=self.tenant.user_id,
            role=self.tenant.role,
        )


def parse_config(raw: object) -> HoundexConfig:
    """Parse + validate raw config (accepts camelCase aliases or snake_case)."""
    return HoundexConfig.model_validate(raw)


def default_config(adapter: str = "local", tenant_id: str | None = None) -> HoundexConfig:
    data: dict[str, Any] = {"adapter": adapter}
    if tenant_id:
        data["tenant"] = {"tenantId": tenant_id}
    return HoundexConfig.model_validate(data)
