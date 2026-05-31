-- houndex storage-supabase — initial schema.
--
-- Postgres + pgvector. Every table carries `tenant_id` and is covered by a
-- row-level-security policy keyed on the request's `tenant_id` JWT claim, so
-- anon/authenticated keys can never read across tenants. (A service-role key
-- bypasses RLS; the client adapter additionally filters every query by
-- tenant_id, so isolation holds on both paths.)
--
-- The embedding dimension below (1536) matches OpenAI text-embedding-3-small.
-- Change it to match your embedding model before applying.

create extension if not exists vector with schema extensions;

-- ── tenancy ────────────────────────────────────────────────────────────
create table if not exists houndex_tenants (
  tenant_id  text primary key,
  created_at bigint not null
);

create table if not exists houndex_runs (
  tenant_id  text not null,
  run_id     text not null,
  subject    text not null,
  signal     text,
  status     text not null check (status in ('pending','running','complete','failed')),
  created_at bigint not null,
  reason     text,
  primary key (tenant_id, run_id)
);

-- ── evidence store ─────────────────────────────────────────────────────
create table if not exists houndex_claims (
  tenant_id     text not null,
  claim_id      text not null,
  subject       text not null,
  category      text not null,
  polarity      text not null,
  scope         text not null,
  claim_text    text not null,
  evidence_text text not null,
  confidence    text not null,
  source_url    text not null,
  source_tier   text not null,
  extracted_at  bigint not null,
  embedding     extensions.vector(1536),
  primary key (tenant_id, claim_id)
);
create index if not exists houndex_claims_by_subject
  on houndex_claims (tenant_id, subject);
-- Cosine-distance ANN index for vector search (HNSW).
create index if not exists houndex_claims_by_embedding
  on houndex_claims using hnsw (embedding extensions.vector_cosine_ops);

create table if not exists houndex_sources (
  tenant_id  text not null,
  source_id  text not null,
  url        text not null,
  title      text not null default '',
  domain     text not null default '',
  tier       text not null,
  fetched_at bigint not null,
  primary key (tenant_id, source_id)
);

create table if not exists houndex_edges (
  tenant_id       text not null,
  idempotency_key text not null,
  src_id          text not null,
  dst_id          text not null,
  kind            text not null,
  attributes      jsonb not null default '{}'::jsonb,
  primary key (tenant_id, idempotency_key)
);

-- ── human curation + knowledge base ──────────────────────────────────────
create table if not exists houndex_curation_suggestions (
  tenant_id     text not null,
  suggestion_id text not null,
  claim         jsonb not null,
  status        text not null check (status in ('pending','approved','edited','rejected')),
  rationale     text,
  created_at    bigint not null,
  decided_at    bigint,
  reason        text,
  primary key (tenant_id, suggestion_id)
);

create table if not exists houndex_kb_entries (
  tenant_id  text not null,
  entry_id   text not null,
  claim      jsonb not null,
  status     text not null check (status in ('pending','approved','edited','rejected')),
  subject    text not null,
  category   text not null,
  updated_at bigint not null,
  primary key (tenant_id, entry_id)
);
create index if not exists houndex_kb_entries_by_subject
  on houndex_kb_entries (tenant_id, subject);

create table if not exists houndex_verification_overrides (
  id         bigint generated always as identity primary key,
  tenant_id  text not null,
  claim_id   text not null,
  verdict    text not null check (verdict in ('red','yellow','green')),
  reason     text not null,
  created_at bigint not null
);
create index if not exists houndex_verification_overrides_by_claim
  on houndex_verification_overrides (tenant_id, claim_id);

-- ── tenant-scoped vector search ──────────────────────────────────────────
-- Returns the nearest claims for a tenant by cosine distance, optionally
-- filtered by subject/category. Called from the adapter via `.rpc()`.
create or replace function houndex_search_claims (
  p_tenant_id text,
  query_embedding extensions.vector(1536),
  match_count int default 10,
  p_subject text default null,
  p_category text default null
)
returns setof houndex_claims
language sql stable
as $$
  select *
  from houndex_claims c
  where c.tenant_id = p_tenant_id
    and (p_subject is null or c.subject = p_subject)
    and (p_category is null or c.category = p_category)
    and c.embedding is not null
  order by c.embedding <=> query_embedding
  limit match_count;
$$;

-- ── row-level security ─────────────────────────────────────────────────
-- Each policy restricts rows to the tenant in the request's JWT claim. Apply
-- with anon/authenticated keys; a trusted server using the service-role key
-- bypasses RLS and relies on the adapter's explicit tenant_id filters.
do $$
declare t text;
begin
  foreach t in array array[
    'houndex_tenants','houndex_runs','houndex_claims','houndex_sources',
    'houndex_edges','houndex_curation_suggestions','houndex_kb_entries',
    'houndex_verification_overrides'
  ] loop
    execute format('alter table %I enable row level security;', t);
    execute format(
      'create policy tenant_isolation on %I using (tenant_id = (auth.jwt() ->> ''tenant_id''));',
      t
    );
  end loop;
end $$;
