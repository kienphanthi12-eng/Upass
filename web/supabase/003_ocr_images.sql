-- ================================================================
-- Migration 003: Public bucket cho ảnh từ OCR
-- Chạy file này trong Supabase SQL Editor
-- ================================================================

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'ocr-images',
  'ocr-images',
  true,   -- public: ảnh có thể xem không cần auth
  10485760, -- 10MB per image
  ARRAY['image/jpeg','image/png','image/gif','image/webp','image/svg+xml']
)
ON CONFLICT (id) DO NOTHING;

-- Giáo viên được upload ảnh
CREATE POLICY "ocr_images_teacher_upload" ON storage.objects
  FOR INSERT WITH CHECK (
    bucket_id = 'ocr-images'
    AND auth.uid() IS NOT NULL
    AND EXISTS (SELECT 1 FROM teachers WHERE id = auth.uid())
  );

-- Ai cũng đọc được (học sinh xem đề cần thấy ảnh)
CREATE POLICY "ocr_images_public_read" ON storage.objects
  FOR SELECT USING (bucket_id = 'ocr-images');

-- Giáo viên xóa ảnh của mình
CREATE POLICY "ocr_images_teacher_delete" ON storage.objects
  FOR DELETE USING (
    bucket_id = 'ocr-images'
    AND auth.uid() IS NOT NULL
    AND (storage.foldername(name))[1] = auth.uid()::text
  );
