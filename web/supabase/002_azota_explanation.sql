-- ================================================================
-- Migration 002: Hỗ trợ pipeline Azota cho draft_questions
-- Thêm cột explanation (lời giải) + needs_review (cờ giáo viên cần review)
-- Chạy trong Supabase SQL Editor
-- ================================================================

ALTER TABLE draft_questions ADD COLUMN IF NOT EXISTS explanation TEXT;
ALTER TABLE draft_questions ADD COLUMN IF NOT EXISTS needs_review BOOLEAN DEFAULT false;
ALTER TABLE draft_questions ADD COLUMN IF NOT EXISTS review_reason TEXT;

-- Cho phép lưu môn học khi tạo draft từ Azota (nếu chưa có default phù hợp)
-- subject_id đã tồn tại trong draft_exams (default 1) — không cần thêm.
