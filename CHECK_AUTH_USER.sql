-- ================================================================
-- CHECK: Does the auth user exist?
-- Run this FIRST
-- ================================================================

SELECT 
    email,
    id,
    email_confirmed_at,
    created_at
FROM auth.users 
WHERE email = 'teacher.test@thptkimngoc.edu.vn';

-- If this returns NO ROWS, the user doesn't exist yet!
-- You MUST create it via the Dashboard UI (can't create auth users via SQL)
