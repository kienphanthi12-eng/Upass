-- ================================================================
-- FIX: Convert Student Account to Teacher Account
-- Run this in Supabase SQL Editor
-- ================================================================

-- Step 1: Delete from students table (if exists)
DELETE FROM students 
WHERE email = 'teacher.test@thptkimngoc.edu.vn';

-- Step 2: Insert into teachers table
INSERT INTO teachers (id, full_name, email)
SELECT id, 'Giáo Viên Test', 'teacher.test@thptkimngoc.edu.vn'
FROM auth.users 
WHERE email = 'teacher.test@thptkimngoc.edu.vn'
ON CONFLICT (id) DO NOTHING;

-- Step 3: Verify
SELECT 
    '✅ Account Converted to Teacher!' as status,
    t.id,
    t.full_name,
    t.email,
    t.created_at
FROM teachers t
WHERE t.email = 'teacher.test@thptkimngoc.edu.vn';

-- ================================================================
-- SUCCESS! Now login will redirect to teacher dashboard
-- URL: http://localhost:3000/login
-- Email: teacher.test@thptkimngoc.edu.vn
-- Password: Test@123456
-- ================================================================
