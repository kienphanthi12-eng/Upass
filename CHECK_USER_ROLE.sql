-- ================================================================
-- DIAGNOSE: Is this account a student or teacher?
-- Run this in Supabase SQL Editor
-- ================================================================

-- Check if user exists in students table
SELECT 
    'Student Check' as check_type,
    CASE 
        WHEN COUNT(*) > 0 THEN '✅ User is in students table'
        ELSE '❌ User is NOT in students table'
    END as result,
    COUNT(*) as count
FROM students 
WHERE email = 'teacher.test@thptkimngoc.edu.vn';

-- Check if user exists in teachers table
SELECT 
    'Teacher Check' as check_type,
    CASE 
        WHEN COUNT(*) > 0 THEN '✅ User is in teachers table'
        ELSE '❌ User is NOT in teachers table'
    END as result,
    COUNT(*) as count
FROM teachers 
WHERE email = 'teacher.test@thptkimngoc.edu.vn';

-- Show which table the user is in
SELECT 
    u.email,
    u.id,
    CASE 
        WHEN s.id IS NOT NULL THEN 'STUDENT'
        WHEN t.id IS NOT NULL THEN 'TEACHER'
        ELSE 'NEITHER'
    END as user_role,
    s.full_name as student_name,
    t.full_name as teacher_name
FROM auth.users u
LEFT JOIN students s ON u.id = s.id
LEFT JOIN teachers t ON u.id = t.id
WHERE u.email = 'teacher.test@thptkimngoc.edu.vn';
