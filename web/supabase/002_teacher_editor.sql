-- ================================================================
-- Migration 002: Teacher PDF Editor
-- Chạy file này trong Supabase SQL Editor
-- ================================================================

-- Thêm cột pdf_storage_path vào ocr_jobs
ALTER TABLE ocr_jobs ADD COLUMN IF NOT EXISTS pdf_storage_path TEXT;

-- ================================================================
-- Supabase Storage: bucket teacher-pdfs
-- ================================================================

-- Tạo bucket (nếu chưa có)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'teacher-pdfs',
  'teacher-pdfs',
  false,
  52428800,
  ARRAY['application/pdf']
) ON CONFLICT (id) DO NOTHING;

-- Giáo viên upload PDF của mình (path: {userId}/{jobId}.pdf)
CREATE POLICY "teacher_pdfs_upload" ON storage.objects
  FOR INSERT WITH CHECK (
    bucket_id = 'teacher-pdfs'
    AND auth.uid()::text = (storage.foldername(name))[1]
    AND EXISTS (SELECT 1 FROM public.teachers WHERE id = auth.uid())
  );

-- Giáo viên chỉ đọc file của mình
CREATE POLICY "teacher_pdfs_own_read" ON storage.objects
  FOR SELECT USING (
    bucket_id = 'teacher-pdfs'
    AND auth.uid()::text = (storage.foldername(name))[1]
  );

-- Giáo viên xóa file của mình
CREATE POLICY "teacher_pdfs_own_delete" ON storage.objects
  FOR DELETE USING (
    bucket_id = 'teacher-pdfs'
    AND auth.uid()::text = (storage.foldername(name))[1]
  );
