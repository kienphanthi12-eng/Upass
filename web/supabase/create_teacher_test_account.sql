-- ================================================================
-- CREATE TEACHER TEST ACCOUNT
-- Chạy file này trong Supabase SQL Editor
-- ================================================================

-- Step 1: Tạo tài khoản auth (chạy trong Supabase Dashboard > Authentication > Users > Add User)
-- Hoặc dùng API script bên dưới (Python)

-- Step 2: Sau khi có user trong auth.users, chạy lệnh này:
-- Thay thế email và tên giáo viên

INSERT INTO teachers (id, full_name, email)
SELECT id, 'Giáo Viên Test', 'teacher.test@thptkimngoc.edu.vn'
FROM auth.users 
WHERE email = 'teacher.test@thptkimngoc.edu.vn'
ON CONFLICT (id) DO NOTHING;

-- ================================================================
-- KIỂM TRA
-- ================================================================

-- Xem danh sách giáo viên
SELECT 
  t.id,
  t.full_name,
  t.email,
  t.created_at,
  u.email as auth_email
FROM teachers t
LEFT JOIN auth.users u ON t.id = u.id;

-- ================================================================
-- MẬT KHẨU MẶC ĐỊNH: Test@123456
-- ================================================================
