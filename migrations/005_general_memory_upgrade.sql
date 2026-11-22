alter table public.user_memories
    add column if not exists importance double precision not null default 0.7;

create index if not exists user_memories_cat_idx
    on public.user_memories (user_id, memory_type, is_current, confirmed);

create index if not exists user_memories_importance_idx
    on public.user_memories (user_id, importance desc, updated_at desc);

notify pgrst, 'reload schema';
