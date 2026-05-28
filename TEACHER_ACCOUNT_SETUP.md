# 👨‍🏫 Tạo Tài Khoản Giáo Viên Test

## 📋 Thông Tin Tài Khoản

| Trường | Giá trị |
|--------|---------|
| **Email** | `teacher.test@thptkimngoc.edu.vn` |
| **Password** | `Test@123456` |
| **Name** | `Giáo Viên Test` |
| **Role** | Teacher |

---

## 🚀 Cách Tạo Tài Khoản

### **Cách 1: Tự động (Recommended)**

1. **Cài đặt supabase package:**
   ```bash
   pip install supabase
   ```

2. **Kiểm tra file `web/.env.local` có đầy đủ:**
   ```env
   NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
   ```

3. **Chạy script:**
   ```bash
   python create_teacher_test_account.py
   ```

4. **Kết quả:**
   ```
   ✅ TEACHER ACCOUNT CREATED SUCCESSFULLY!
   
   📧 Email:    teacher.test@thptkimngoc.edu.vn
   🔑 Password: Test@123456
   👤 Name:     Giáo Viên Test
   
   🌐 Login URL: http://localhost:3000/login
   📊 Dashboard: http://localhost:3000/teacher/dashboard
   ```

---

### **Cách 2: Thủ công qua Supabase Dashboard**

1. **Truy cập Supabase Dashboard:**
   - Mở: https://app.supabase.com
   - Chọn project của bạn

2. **Tạo Auth User:**
   - Vào **Authentication** > **Users**
   - Click **Add user** > **Create new user**
   - Điền thông tin:
     - Email: `teacher.test@thptkimngoc.edu.vn`
     - Password: `Test@123456`
     - ✅ Auto Confirm User (bỏ qua email verification)
   - Click **Create user**
   - Copy **User ID** (UUID)

3. **Tạo Teacher Record:**
   - Vào **SQL Editor**
   - Chạy query sau (thay `USER_ID` bằng UUID vừa copy):
   
   ```sql
   INSERT INTO teachers (id, full_name, email)
   VALUES ('USER_ID', 'Giáo Viên Test', 'teacher.test@thptkimngoc.edu.vn');
   ```

4. **Kiểm tra:**
   ```sql
   SELECT t.*, u.email as auth_email
   FROM teachers t
   LEFT JOIN auth.users u ON t.id = u.id
   WHERE t.email = 'teacher.test@thptkimngoc.edu.vn';
   ```

---

### **Cách 3: SQL Only**

Chạy file SQL:
```bash
# Copy nội dung file này vào Supabase SQL Editor
cat web/supabase/create_teacher_test_account.sql
```

---

## ✅ Kiểm Tra Tài Khoản

### **1. Trong Database:**
```sql
SELECT 
  t.id,
  t.full_name,
  t.email,
  t.created_at,
  u.email as auth_email
FROM teachers t
LEFT JOIN auth.users u ON t.id = u.id;
```

### **2. Trên Web Interface:**

1. **Start development server:**
   ```bash
   cd web
   npm run dev
   ```

2. **Mở browser:**
   - Login: http://localhost:3000/login
   - Email: `teacher.test@thptkimngoc.edu.vn`
   - Password: `Test@123456`

3. **Sau khi login:**
   - Sẽ được redirect tới: `/teacher/dashboard`
   - Có thể upload PDF, xem đề thi, giao bài tập

---

## 🎯 Teacher Features

Sau khi login, giáo viên có thể:

### **1. Dashboard (`/teacher/dashboard`)**
- Xem tổng quan đề thi đã tạo
- Thống kê số lượng câu hỏi
- Xem bài tập đã giao

### **2. Upload PDF (`/teacher/upload`)**
- Upload đề thi PDF
- Tự động OCR qua MinerU
- Chuẩn hóa nội dung bằng AI
- Trích xuất câu hỏi tự động

### **3. Editor**
- Chỉnh sửa câu hỏi
- Thêm/sửa options
- Điền đáp án
- Phân loại mức độ

### **4. Assignments**
- Giao đề cho lớp học sinh
- Theo dõi tiến độ làm bài
- Xem kết quả

---

## 🔧 Troubleshooting

### **Lỗi: Missing SUPABASE_URL**
```
❌ Error: Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY
```
**Fix:** Kiểm tra file `web/.env.local` có đầy đủ biến môi trường

### **Lỗi: User already exists**
```
⚠️  User already exists, fetching user ID...
✅ Found existing user: xxx-xxx-xxx
```
**Fix:** Tài khoản đã tồn tại, có thể login được luôn

### **Lỗi: teachers table does not exist**
**Fix:** Chạy migration trước:
```sql
-- Trong Supabase SQL Editor
-- Run: web/supabase/001_teacher_ocr.sql
-- Run: web/supabase/002_teacher_editor.sql
```

### **Lỗi: Login không vào được teacher dashboard**
**Fix:** Kiểm tra teacher record đã tồn tại:
```sql
SELECT * FROM teachers WHERE email = 'teacher.test@thptkimngoc.edu.vn';
```

---

## 📚 Related Files

- `create_teacher_test_account.py` - Script tự động tạo tài khoản
- `web/supabase/create_teacher_test_account.sql` - SQL script
- `web/supabase/001_teacher_ocr.sql` - Migration teachers table
- `web/supabase/002_teacher_editor.sql` - Migration storage & policies
- `web/src/app/teacher/` - Teacher web interface

---

## 🔐 Security Note

⚠️ **Đây là tài khoản test**, chỉ dùng cho development!

**Cho production:**
- ✅ Dùng email thật
- ✅ Password mạnh (>12 ký tự, có special chars)
- ✅ Enable email confirmation
- ✅ Setup 2FA nếu cần

---

## 📞 Support

Nếu gặp vấn đề:
1. Kiểm tra logs trong terminal
2. Xem Supabase logs trong Dashboard
3. Kiểm tra browser console (F12)

---

**Chúc bạn thành công! 🎉**
