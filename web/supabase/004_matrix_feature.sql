-- ============================================================
-- 004_matrix_feature.sql
-- Thêm field topic vào draft_questions (từ DeepSeek extraction)
-- Tạo bảng question_usage cho weighted sampling (V3)
-- ============================================================

-- 1. Thêm cột topic vào draft_questions (lưu tên chủ đề từ DeepSeek)
ALTER TABLE draft_questions
  ADD COLUMN IF NOT EXISTS topic TEXT DEFAULT NULL;

-- 2. Tạo bảng question_usage — track câu nào đã dùng trong đề nào, khi nào
CREATE TABLE IF NOT EXISTS question_usage (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  question_id   INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  teacher_id    UUID    NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  exam_id       INTEGER REFERENCES exams(id) ON DELETE SET NULL,
  draft_exam_id UUID    REFERENCES draft_exams(id) ON DELETE SET NULL,
  used_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_question_usage_question_id ON question_usage(question_id);
CREATE INDEX IF NOT EXISTS idx_question_usage_teacher_id  ON question_usage(teacher_id);
CREATE INDEX IF NOT EXISTS idx_question_usage_used_at     ON question_usage(used_at DESC);

-- RLS
ALTER TABLE question_usage ENABLE ROW LEVEL SECURITY;

CREATE POLICY "teacher_own_usage" ON question_usage
  FOR ALL
  USING (teacher_id = auth.uid())
  WITH CHECK (teacher_id = auth.uid());

-- 3. Index bổ sung trên questions để sampling nhanh hơn
CREATE INDEX IF NOT EXISTS idx_questions_topic_level
  ON questions(topic_id, level)
  WHERE correct_answer IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_questions_subject_level
  ON questions(subject_id, level)
  WHERE correct_answer IS NOT NULL;
