-- Migration 007: User Health Profiles & Strict Row Level Security
-- Establishes single-user health profile storage and enforces account isolation

create table if not exists public.user_profiles (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users (id) on delete cascade unique,
    full_name text not null default '',
    age integer,
    date_of_birth date,
    sex text default 'prefer_not_to_say',
    height double precision,
    current_weight double precision,
    unit_preference text default 'metric',
    primary_goal text default '',
    goals text[] default array[]::text[],
    activity_level text default 'sedentary',
    dietary_preference text default 'any',
    allergies text default '',
    medical_conditions text default '',
    medications text default '',
    injuries_limitations text default '',
    sleep_duration_hours double precision,
    sleep_quality text default '',
    lifestyle_notes text default '',
    onboarding_completed boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists user_profiles_user_idx on public.user_profiles (user_id);

alter table public.user_profiles enable row level security;

grant select, insert, update, delete on table public.user_profiles to authenticated;

drop policy if exists user_profiles_all_own on public.user_profiles;
create policy user_profiles_all_own on public.user_profiles
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

notify pgrst, 'reload schema';
