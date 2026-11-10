update public.user_memories
set memory_key = 'weight'
where memory_key is null
  and lower(memory_content) like '%weight%';

update public.user_memories
set memory_key = 'height'
where memory_key is null
  and lower(memory_content) like '%height%';

update public.user_memories
set memory_key = 'age'
where memory_key is null
  and (
    lower(memory_content) like '% age %'
    or lower(memory_content) like '%years old%'
  );

update public.user_memories older
set is_current = false
from public.user_memories newer
where older.user_id = newer.user_id
  and older.memory_key = newer.memory_key
  and older.id <> newer.id
  and older.is_current
  and newer.is_current
  and (
    (newer.confirmed and not older.confirmed)
    or newer.updated_at > older.updated_at
  )
  and older.updated_at < newer.updated_at;
