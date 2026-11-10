-- Apply this migration to an existing Supabase project that predates
-- conversation-linked memory records.
alter table public.user_memories
    add column if not exists conversation_id uuid
    references public.conversations (id) on delete cascade;

alter table public.goals
    add column if not exists conversation_id uuid
    references public.conversations (id) on delete cascade;

alter table public.recommendations
    add column if not exists conversation_id uuid
    references public.conversations (id) on delete cascade;

alter table public.commitments
    add column if not exists conversation_id uuid
    references public.conversations (id) on delete cascade;

alter table public.outcomes
    add column if not exists conversation_id uuid
    references public.conversations (id) on delete cascade;

alter table public.obstacles
    add column if not exists conversation_id uuid
    references public.conversations (id) on delete cascade;

notify pgrst, 'reload schema';
