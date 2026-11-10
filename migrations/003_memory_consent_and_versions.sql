alter table public.user_memories
    add column if not exists confirmed boolean not null default true;
alter table public.user_memories
    add column if not exists is_current boolean not null default true;
alter table public.user_memories
    add column if not exists memory_key text;
alter table public.user_memories
    add column if not exists superseded_by uuid references public.user_memories (id) on delete set null;

create index if not exists user_memories_current_idx
    on public.user_memories (user_id, is_current, confirmed, updated_at desc);
create index if not exists user_memories_key_idx
    on public.user_memories (user_id, memory_key, is_current);
