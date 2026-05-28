-- ================================================================
-- DIAGNOSE TEACHER LOGIN ISSUE
-- Run this in Supabase SQL Editor
-- ================================================================

-- Check 1: Does auth user exist?
SELECT 
    'Auth User Check' as check_name,
    CASE 
        WHEN COUNT(*) > 0 THEN '✅ User exists in auth.users'
        ELSE '❌ User NOT found - Need to create auth user first'
    END as status,
    COUNT(*) as count
FROM auth.users 
WHERE email = 'teacher.test@thptkimngoc.edu.vn';

-- Check 2: Is the user confirmed?
SELECT 
    'Email Confirmation Check' as check_name,
    CASE 
        WHEN email_confirmed_at IS NOT NULL THEN '✅ Email confirmed'
        ELSE '❌ Email NOT confirmed - Must tick "Auto Confirm User"'
    END as status,
    email_confirmed_at
FROM auth.users 
WHERE email = 'teacher.test@thptkimngoc.edu.vn';

-- Check 3: Does teacher record exist?
SELECT 
    'Teacher Record Check' as check_name,
    CASE 
        WHEN COUNT(*) > 0 THEN '✅ Teacher record exists'
        ELSE '❌ Teacher record NOT found - Need to INSERT into teachers table'
    END as status,
    COUNT(*) as count
FROM teachers 
WHERE email = 'teacher.test@thptkimngoc.edu.vn';

-- Check 4: Show all teachers (if any)
SELECT 
    'All Teachers' as info,
    t.id,
    t.full_name,
    t.email,
    u.email_confirmed_at
FROM teachers t
LEFT JOIN auth.users u ON t.id = u.id;

-- ================================================================
-- FIX INSTRUCTIONS (based on results):
-- ================================================================

-- IF "User NOT found":
-- 1. Go to: https://app.supabase.com/project/zabvdgnucfanvbjjgnic/auth/users
-- 2. Click "Add user" > "Create new user"
-- 3. Fill:
--    Email: teacher.test@thptkimngoc.edu.vn
--    Password: Test@123456
--    ✅ CHECK "Auto Confirm User" (VERY IMPORTANT!)
-- 4. Click "Create user"

-- IF "Email NOT confirmed":
-- Delete the user and recreate with "Auto Confirm User" checked

-- IF "Teacher record NOT found":
-- Run this SQL:
-- INSERT INTO teachers (id, full_name, email)
-- SELECT id, 'Giáo Viên Test', 'teacher.test@thptkimngoc.edu.vn'
-- FROM auth.users 
-- WHERE email = 'teacher.test@thptkimngoc.edu.vn';
