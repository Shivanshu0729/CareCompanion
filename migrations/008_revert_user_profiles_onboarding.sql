-- Migration 008: Safe rollback for user_profiles onboarding requirements
--
-- This rollback migration safely detaches the application from mandatory health onboarding.
-- In accordance with safety policies:
-- 1. Existing tables and user data in user_profiles are preserved (no DROP TABLE or DELETE).
-- 2. Row Level Security (RLS) on user_profiles remains enabled to prevent data exposure.
-- 3. Application code no longer requires or enforces onboarding or third-party query refusals.

-- Notify PostgREST schema cache to reload
notify pgrst, 'reload schema';
