-- ================================================================
-- FIX: CREATE TEACHER RECORD
-- Run this in Supabase SQL Editor
-- ================================================================

-- This will create the teacher record linked to the existing auth user
INSERT INTO teachers (id, full_name, email)
SELECT id, 'Giáo Viên Test', 'teacher.test@thptkimngoc.edu.vn'
FROM auth.users 
WHERE email = 'teacher.test@thptkimngoc.edu.vn'
ON CONFLICT (id) DO NOTHING;

-- Verify it worked
SELECT 
    '✅ Teacher Record Created!' as status,
    t.id,
    t.full_name,
    t.email,
    t.created_at
FROM teachers t
WHERE t.email = 'teacher.test@thptkimngoc.edu.vn';

-- ================================================================
-- SUCCESS! Now you can login:
-- URL: http://localhost:3000/login
-- Email: teacher.test@thptkimngoc.edu.vn
-- Password: Test@123456
-- ================================================================
