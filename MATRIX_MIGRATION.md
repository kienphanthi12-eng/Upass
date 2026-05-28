# Hướng dẫn chạy Migration 004

## Mục đích
Migration này thêm 2 thứ:
1. Cột `topic` vào bảng `draft_questions` — lưu chủ đề từ DeepSeek
2. Bảng `question_usage` — track câu đã dùng để weighted sampling

## Cách chạy

### Cách 1: Supabase Dashboard (khuyến nghị)
1. Vào https://supabase.com/dashboard → chọn project
2. Vào **SQL Editor**
3. Copy nội dung file `web/supabase/004_matrix_feature.sql`
4. Paste vào editor → Run

### Cách 2: Supabase CLI
```bash
supabase db push
```

## Kiểm tra sau khi chạy
Chạy query này để verify:
```sql
-- Kiểm tra cột topic đã có
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'draft_questions' AND column_name = 'topic';

-- Kiểm tra bảng question_usage
SELECT table_name FROM information_schema.tables 
WHERE table_name = 'question_usage';
```
