-- Run in Supabase SQL editor (or psql) once per project.
create table if not exists public.leaderboard_scores (
  id uuid primary key default gen_random_uuid(),
  corp_name text not null,
  user_id text not null,
  user_name text not null,
  best_score integer not null check (best_score >= 0),
  updated_at timestamptz not null default now(),
  unique (corp_name, user_id)
);

create index if not exists leaderboard_scores_corp_best_idx
  on public.leaderboard_scores (corp_name, best_score desc);

-- RLS on with no permissive policies: only the service role (used by this app) can access.
alter table public.leaderboard_scores enable row level security;

create or replace function public.set_leaderboard_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists leaderboard_scores_set_updated on public.leaderboard_scores;
create trigger leaderboard_scores_set_updated
before update on public.leaderboard_scores
for each row execute function public.set_leaderboard_updated_at();
