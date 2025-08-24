-- One row per product – authoritative SDS facts parsed from the PDF
--------------------------------------------------------------------------------
create table public.sds_metadata (
  -- Surrogate FK to product
  product_id            integer primary key
                         references public.product(id)
                         on delete cascade,

  -- Key fields
  vendor                text,
  issue_date            date,
  hazardous_substance   boolean,
  dangerous_good        boolean,
  dangerous_goods_class text,
  description           text,
  packing_group         text,
  subsidiary_risks      text,

  -- Full parse cache (optional)
  raw_json              jsonb,

  -- Audit
  created_at            timestamptz default timezone('utc', now())
);

--------------------------------------------------------------------------------
-- Helpful indexes
--------------------------------------------------------------------------------
create index if not exists idx_sds_metadata_issue_date
  on public.sds_metadata(issue_date);

create index if not exists idx_sds_metadata_vendor
  on public.sds_metadata(vendor);

create index if not exists idx_sds_metadata_hazardous_substance
  on public.sds_metadata(hazardous_substance);

create index if not exists idx_sds_metadata_dangerous_good
  on public.sds_metadata(dangerous_good);

-- JSON / full-text acceleration
create index if not exists idx_sds_metadata_raw_json
  on public.sds_metadata using gin (raw_json);
