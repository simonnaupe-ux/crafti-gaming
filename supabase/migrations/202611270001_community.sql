-- Preparación únicamente. Revisar privacidad y elegibilidad antes de activar registros.
begin;
create table public.crafti_members (
 id uuid primary key references auth.users(id) on delete cascade,
 nickname text not null check (char_length(nickname) between 2 and 32),
 created_at timestamptz not null default now()
);
create table public.crafti_badges (
 member_id uuid references public.crafti_members(id) on delete cascade,
 badge text not null,
 awarded_at timestamptz not null default now(),
 primary key(member_id,badge)
);
create table public.crafti_events (
 id uuid primary key default gen_random_uuid(),
 title text not null,
 enabled boolean not null default false
);
alter table public.crafti_members enable row level security;
alter table public.crafti_badges enable row level security;
alter table public.crafti_events enable row level security;
revoke all on public.crafti_members, public.crafti_badges, public.crafti_events from anon, authenticated;
-- No client access until explicit activation and security review.
commit;
