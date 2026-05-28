# 🚀 TẠO TÀI KHOẢN GIÁO VIÊN - HƯỚNG DẪN NHANH

## ⚠️ Vấn Đề Hiện Tại

Bạn đang gặp lỗi: **"Email hoặc mật khẩu không đúng"** vì tài khoản giáo viên chưa được tạo trong Supabase.

---

## ✅ Cách Tạo (3 Bước Đơn Giản)

### **Bước 1: Lấy Service Role Key**

1. Mở: https://app.supabase.com
2. Chọn project: `zabvdgnucfanvbjjgnic`
3. Vào: **Settings** (icon bánh răng ⚙️) > **API**
4. Copy **service_role** key (bí mật, không chia sẻ!)
5. Paste vào file `web/.env.local`:
   ```env
   SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOi... (dài ~200 ký tự)
   ```

---

### **Bước 2: Chạy Script Tạo Account**

```bash
# Cài supabase package (nếu chưa có)
pip install supabase

# Chạy script
python create_teacher_test_account.py
```

**Hoặc** nếu không muốn cài thêm package, dùng **Bước 2 Alternative** 👇

---

### **Bước 2 Alternative: Tạo Thủ Công Qua Dashboard**

1. **Tạo Auth User:**
   - Vào: https://app.supabase.com/project/zabvdgnucfanvbjjgnic/auth/users
   - Click **Add user** > **Create new user**
   - Điền:
     - Email: `teacher.test@thptkimngoc.edu.vn`
     - Password: `Test@123456`
     - ✅ **Auto Confirm User** (quan trọng!)
   - Click **Create user**
   - **Copy User ID** (UUID, ví dụ: `abc123-def456-ghi789`)

2. **Tạo Teacher Record:**
   - Vào: https://app.supabase.com/project/zabvdgnucfanvbjjgnic/sql
   - Paste SQL này (thay `YOUR_USER_ID` bằng UUID vừa copy):
   
   ```sql
   INSERT INTO teachers (id, full_name, email)
   VALUES ('YOUR_USER_ID', 'Giáo Viên Test', 'teacher.test@thptkimngoc.edu.vn');
   ```
   
   - Click **Run**

3. **Kiểm Tra:**
   ```sql
   SELECT t.*, u.email 
   FROM teachers t 
   JOIN auth.users u ON t.id = u.id 
   WHERE t.email = 'teacher.test@thptkimngoc.edu.vn';
   ```
   
   Phải thấy 1 dòng kết quả! ✅

---

### **Bước 3: Login & Test**

```bash
# 1. Đảm bảo web server đang chạy
cd web
npm run dev

# 2. Mở browser
http://localhost:3000/login

# 3. Đăng nhập
Email: teacher.test@thptkimngoc.edu.vn
Password: Test@123456

# 4. Thành công! Sẽ vào: http://localhost:3000/teacher/dashboard
```

---

## 🔍 Troubleshooting

### ❌ Lỗi: "teachers table does not exist"

**Nguyên nhân:** Chưa chạy migration

**Fix:**
1. Vào: https://app.supabase.com/project/zabvdgnucfanvbjjgnic/sql/new
2. Copy toàn bộ file: `web/supabase/001_teacher_ocr.sql`
3. Paste và Run
4. Copy toàn bộ file: `web/supabase/002_teacher_editor.sql`  
5. Paste và Run

---

### ❌ Lỗi: "User already confirmed" hoặc không login được

**Nguyên nhân:** Chưa tick "Auto Confirm User"

**Fix:**
1. Vào: https://app.supabase.com/project/zabvdgnucfanvbjjgnic/auth/users
2. Xóa user cũ (nếu có)
3. Tạo lại user mới, **NHỚ TICK** ✅ Auto Confirm User

---

### ❌ Lỗi: Login xong bị redirect về `/dashboard` thay vì `/teacher/dashboard`

**Nguyên nhân:** Teacher record chưa tồn tại trong database

**Fix:**
```sql
-- Kiểm tra
SELECT * FROM teachers WHERE email = 'teacher.test@thptkimngoc.edu.vn';

-- Nếu không có kết quả, chạy:
INSERT INTO teachers (id, full_name, email)
SELECT id, 'Giáo Viên Test', 'teacher.test@thptkimngoc.edu.vn'
FROM auth.users 
WHERE email = 'teacher.test@thptkimngoc.edu.vn';
```

---

## 📋 Checklist

- [ ] Đã lấy Service Role Key từ Supabase Dashboard
- [ ] Đã update `web/.env.local` với key thật
- [ ] Đã chạy migrations (`001_teacher_ocr.sql`, `002_teacher_editor.sql`)
- [ ] Đã tạo Auth User trong Supabase
- [ ] Đã tạo Teacher record trong bảng `teachers`
- [ ] Đã test login thành công

---

## 🎯 Thông Tin Account

```
Email:    teacher.test@thptkimngoc.edu.vn
Password: Test@123456
Name:     Giáo Viên Test
Role:     Teacher
```

---

## 📞 Cần Trợ Giúp?

Nếu vẫn gặp lỗi, cung cấp:
1. Screenshot lỗi trong browser
2. Console logs (F12 > Console tab)
3. Kết quả query: `SELECT * FROM teachers;`

---

**Chúc thành công! 🎉**
