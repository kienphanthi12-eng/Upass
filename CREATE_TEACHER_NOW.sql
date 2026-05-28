-- ================================================================
-- CREATE TEACHER ACCOUNT - RUN IN SUPABASE SQL EDITOR
-- ================================================================
-- Instructions:
-- 1. Go to: https://app.supabase.com/project/zabvdgnucfanvbjjgnic/sql/new
-- 2. Paste this entire file
-- 3. Click "Run"
-- ================================================================

-- Step 1: Check if teachers table exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_name = 'teachers'
    ) THEN
        RAISE EXCEPTION 'teachers table does not exist. Please run migrations first: web/supabase/001_teacher_ocr.sql';
    END IF;
END $$;

-- Step 2: Create the teacher account
-- First, we need to create the auth user via Dashboard, then link it

-- CHECK if user already exists in auth.users
DO $$
DECLARE
    user_exists BOOLEAN;
    teacher_exists BOOLEAN;
BEGIN
    -- Check if auth user exists
    SELECT EXISTS(
        SELECT 1 FROM auth.users WHERE email = 'teacher.test@thptkimngoc.edu.vn'
    ) INTO user_exists;
    
    -- Check if teacher record exists
    SELECT EXISTS(
        SELECT 1 FROM teachers WHERE email = 'teacher.test@thptkimngoc.edu.vn'
    ) INTO teacher_exists;
    
    IF user_exists AND teacher_exists THEN
        RAISE NOTICE '✅ Teacher account already exists!';
    ELSIF user_exists AND NOT teacher_exists THEN
        RAISE NOTICE '⚠️  Auth user exists but teacher record is missing. Running INSERT...';
        
        -- Create teacher record
        INSERT INTO teachers (id, full_name, email)
        SELECT id, 'Giáo Viên Test', 'teacher.test@thptkimngoc.edu.vn'
        FROM auth.users 
        WHERE email = 'teacher.test@thptkimngoc.edu.vn'
        ON CONFLICT (id) DO NOTHING;
        
        RAISE NOTICE '✅ Teacher record created successfully!';
    ELSE
        RAISE NOTICE '❌ Auth user does not exist yet.';
        RAISE NOTICE '';
        RAISE NOTICE '📋 Please do this:';
        RAISE NOTICE '1. Go to: https://app.supabase.com/project/zabvdgnucfanvbjjgnic/auth/users';
        RAISE NOTICE '2. Click "Add user" > "Create new user"';
        RAISE NOTICE '3. Fill in:';
        RAISE NOTICE '   - Email: teacher.test@thptkimngoc.edu.vn';
        RAISE NOTICE '   - Password: Test@123456';
        RAISE NOTICE '   - ✅ CHECK "Auto Confirm User"';
        RAISE NOTICE '4. Click "Create user"';
        RAISE NOTICE '5. Come back here and run this SQL again';
    END IF;
END $$;

-- Step 3: Verify
SELECT 
    '✅ Teacher Account Details' as info,
    t.full_name,
    t.email,
    t.created_at
FROM teachers t
WHERE t.email = 'teacher.test@thptkimngoc.edu.vn';

-- ================================================================
-- AFTER SUCCESS:
-- Login at: http://localhost:3000/login
-- Email: teacher.test@thptkimngoc.edu.vn
-- Password: Test@123456
-- ================================================================
