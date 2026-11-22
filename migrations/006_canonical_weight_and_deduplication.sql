-- Migration 006: Canonical Key Normalization, Health Categorization & Single-Value Deduplication
-- Fixes weight categorization (health), canonical key (current_weight), and supersedes older duplicates.

-- 1. Normalize all weight-related records to memory_key = 'current_weight' and memory_type = 'health'
update public.user_memories
set
    memory_key = 'current_weight',
    memory_type = 'health',
    confirmed = true
where
    memory_key in ('weight', 'user_weight', 'body_weight', 'current_body_weight', 'bodyweight', 'weight_kg', 'weight_lbs', 'my_weight')
    or memory_content ilike '%weight%'
    or memory_content ilike '%weigh%';

-- 2. Normalize all name-related records to memory_key = 'name' and memory_type = 'profile'
update public.user_memories
set
    memory_key = 'name',
    memory_type = 'profile',
    confirmed = true
where
    memory_key in ('user_name', 'preferred_name', 'first_name', 'full_name', 'my_name')
    or memory_content ilike 'call me %'
    or memory_content ilike 'my name is %'
    or memory_content ilike 'user''s name is %';

-- 3. For any user with multiple current_weight records marked is_current = true,
-- supersede older ones so only the newest record by updated_at remains is_current = true
with ranked_weights as (
    select
        id,
        user_id,
        row_number() over (partition by user_id order by updated_at desc, created_at desc) as rn,
        first_value(id) over (partition by user_id order by updated_at desc, created_at desc) as latest_id
    from public.user_memories
    where memory_key = 'current_weight'
)
update public.user_memories m
set
    is_current = (rw.rn = 1),
    superseded_by = case when rw.rn > 1 then rw.latest_id else null end
from ranked_weights rw
where m.id = rw.id;

-- 4. Clean up duplicate assistant recommendations stored in user_memories
delete from public.user_memories
where memory_type = 'recommendation'
  and source = 'ai_generated';

notify pgrst, 'reload schema';
