create extension if not exists "pgcrypto";

create table if not exists public.users (
    id uuid primary key references auth.users (id) on delete cascade,
    email text unique not null,
    created_at timestamptz not null default now()
);

create table if not exists public.conversations (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users (id) on delete cascade,
    title text not null default 'New conversation',
    is_pinned boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

alter table public.conversations
    add column if not exists is_pinned boolean not null default false;

create table if not exists public.messages (
    id uuid primary key default gen_random_uuid(),
    conversation_id uuid not null references public.conversations (id) on delete cascade,
    user_id uuid not null references public.users (id) on delete cascade,
    role text not null check (role in ('user', 'assistant', 'system')),
    content text not null,
    created_at timestamptz not null default now()
);

create table if not exists public.user_memories (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users (id) on delete cascade,
    conversation_id uuid references public.conversations (id) on delete cascade,
    memory_type text not null,
    memory_content text not null,
    source text not null default 'user_reported',
    confidence double precision not null default 0.7,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.session_summaries (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users (id) on delete cascade,
    conversation_id uuid not null references public.conversations (id) on delete cascade,
    summary text not null,
    created_at timestamptz not null default now()
);

create table if not exists public.goals (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users (id) on delete cascade,
    conversation_id uuid references public.conversations (id) on delete cascade,
    goal_description text not null,
    status text not null default 'active',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.recommendations (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users (id) on delete cascade,
    conversation_id uuid references public.conversations (id) on delete cascade,
    goal_id uuid references public.goals (id) on delete set null,
    recommendation text not null,
    status text not null default 'proposed',
    created_at timestamptz not null default now()
);

create table if not exists public.commitments (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users (id) on delete cascade,
    conversation_id uuid references public.conversations (id) on delete cascade,
    recommendation_id uuid references public.recommendations (id) on delete set null,
    commitment_description text not null,
    status text not null default 'accepted',
    created_at timestamptz not null default now()
);

create table if not exists public.outcomes (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users (id) on delete cascade,
    conversation_id uuid references public.conversations (id) on delete cascade,
    commitment_id uuid references public.commitments (id) on delete set null,
    reported_outcome text not null,
    created_at timestamptz not null default now()
);

create table if not exists public.obstacles (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users (id) on delete cascade,
    conversation_id uuid references public.conversations (id) on delete cascade,
    goal_id uuid references public.goals (id) on delete set null,
    obstacle_description text not null,
    created_at timestamptz not null default now()
);

alter table public.user_memories
    add column if not exists conversation_id uuid references public.conversations (id) on delete cascade;
alter table public.goals
    add column if not exists conversation_id uuid references public.conversations (id) on delete cascade;
alter table public.recommendations
    add column if not exists conversation_id uuid references public.conversations (id) on delete cascade;
alter table public.commitments
    add column if not exists conversation_id uuid references public.conversations (id) on delete cascade;
alter table public.outcomes
    add column if not exists conversation_id uuid references public.conversations (id) on delete cascade;
alter table public.obstacles
    add column if not exists conversation_id uuid references public.conversations (id) on delete cascade;

create table if not exists public.health_summaries (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users (id) on delete cascade,
    participant_id text not null,
    metric_type text not null,
    metric_value double precision,
    measurement_date date not null,
    source text not null default 'pmdata',
    created_at timestamptz not null default now()
);

create index if not exists conversations_user_updated_idx on public.conversations (user_id, updated_at desc);
create index if not exists messages_conversation_created_idx on public.messages (conversation_id, created_at);
create index if not exists messages_user_idx on public.messages (user_id);
create index if not exists user_memories_user_type_idx on public.user_memories (user_id, memory_type, updated_at desc);
create index if not exists session_summaries_user_idx on public.session_summaries (user_id, created_at desc);
create index if not exists goals_user_status_idx on public.goals (user_id, status);
create index if not exists recommendations_user_idx on public.recommendations (user_id, created_at desc);
create index if not exists commitments_user_idx on public.commitments (user_id, created_at desc);
create index if not exists outcomes_user_idx on public.outcomes (user_id, created_at desc);
create index if not exists obstacles_user_idx on public.obstacles (user_id, created_at desc);
create index if not exists health_summaries_user_date_idx on public.health_summaries (user_id, measurement_date);

alter table public.users enable row level security;
alter table public.conversations enable row level security;
alter table public.messages enable row level security;
alter table public.user_memories enable row level security;
alter table public.session_summaries enable row level security;
alter table public.goals enable row level security;
alter table public.obstacles enable row level security;
alter table public.recommendations enable row level security;
alter table public.commitments enable row level security;
alter table public.outcomes enable row level security;
alter table public.health_summaries enable row level security;

grant select, insert, update on table public.users to authenticated;
grant select, insert, update, delete on table public.conversations to authenticated;
grant select, insert, update, delete on table public.messages to authenticated;
grant select, insert, update, delete on table public.user_memories to authenticated;
grant select, insert, update, delete on table public.session_summaries to authenticated;
grant select, insert, update, delete on table public.goals to authenticated;
grant select, insert, update, delete on table public.recommendations to authenticated;
grant select, insert, update, delete on table public.commitments to authenticated;
grant select, insert, update, delete on table public.outcomes to authenticated;
grant select, insert, update, delete on table public.obstacles to authenticated;
grant select, insert, update, delete on table public.health_summaries to authenticated;

drop policy if exists users_select_own on public.users;
create policy users_select_own on public.users
    for select using (auth.uid() = id);

drop policy if exists users_insert_own on public.users;
create policy users_insert_own on public.users
    for insert with check (auth.uid() = id);

drop policy if exists users_update_own on public.users;
create policy users_update_own on public.users
    for update using (auth.uid() = id) with check (auth.uid() = id);

drop policy if exists conversations_all_own on public.conversations;
create policy conversations_all_own on public.conversations
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists messages_all_own on public.messages;
create policy messages_all_own on public.messages
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists memories_all_own on public.user_memories;
create policy memories_all_own on public.user_memories
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists summaries_all_own on public.session_summaries;
create policy summaries_all_own on public.session_summaries
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists goals_all_own on public.goals;
create policy goals_all_own on public.goals
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists recommendations_all_own on public.recommendations;
create policy recommendations_all_own on public.recommendations
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists commitments_all_own on public.commitments;
create policy commitments_all_own on public.commitments
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists outcomes_all_own on public.outcomes;
create policy outcomes_all_own on public.outcomes
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists obstacles_all_own on public.obstacles;
create policy obstacles_all_own on public.obstacles
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists health_summaries_all_own on public.health_summaries;
create policy health_summaries_all_own on public.health_summaries
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
