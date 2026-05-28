-- ================================================================
-- Migration 001: Teacher OCR Feature
-- Chạy file này trong Supabase SQL Editor
-- ================================================================

-- 1. Teachers table (link to auth.users)
CREATE TABLE IF NOT EXISTS teachers (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  full_name TEXT NOT NULL,
  email TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 2. OCR Jobs — track trạng thái xử lý từng file PDF
CREATE TABLE IF NOT EXISTS ocr_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  teacher_id UUID NOT NULL REFERENCES auth.users(id),
  filename TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  -- pending | uploading | ocr_running | ocr_done | normalizing | extracting | done | error
  mineru_batch_id TEXT,
  mineru_result JSONB,
  markdown TEXT,
  normalized_markdown TEXT,
  error_msg TEXT,
  question_count INT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 3. Draft exams — bản nháp đề thi giáo viên đang chỉnh sửa
CREATE TABLE IF NOT EXISTS draft_exams (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  teacher_id UUID NOT NULL REFERENCES auth.users(id),
  ocr_job_id UUID REFERENCES ocr_jobs(id),
  title TEXT NOT NULL DEFAULT 'Đề chưa đặt tên',
  exam_year INT DEFAULT EXTRACT(YEAR FROM now())::INT,
  exam_type TEXT NOT NULL DEFAULT 'thi_thu',
  subject_id INT DEFAULT 1,
  status TEXT NOT NULL DEFAULT 'draft',
  -- draft | published
  published_exam_id BIGINT REFERENCES exams(id),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 4. Draft questions — câu hỏi nháp có thể chỉnh sửa
CREATE TABLE IF NOT EXISTS draft_questions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  draft_exam_id UUID NOT NULL REFERENCES draft_exams(id) ON DELETE CASCADE,
  question_number INT,
  question_type TEXT NOT NULL DEFAULT 'trac_nghiem',
  content TEXT NOT NULL DEFAULT '',
  options JSONB,
  correct_answer TEXT,
  difficulty_level TEXT DEFAULT 'Nhận biết',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 5. Assignments — giao đề cho lớp học sinh
CREATE TABLE IF NOT EXISTS assignments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  exam_id BIGINT NOT NULL REFERENCES exams(id),
  teacher_id UUID NOT NULL REFERENCES auth.users(id),
  assigned_to TEXT NOT NULL DEFAULT 'all',
  -- 'all' hoặc tên lớp như '10A1', '11B2'
  created_at TIMESTAMPTZ DEFAULT now()
);

-- ================================================================
-- Row Level Security
-- ================================================================

ALTER TABLE teachers ENABLE ROW LEVEL SECURITY;
ALTER TABLE ocr_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE draft_exams ENABLE ROW LEVEL SECURITY;
ALTER TABLE draft_questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE assignments ENABLE ROW LEVEL SECURITY;

-- Teachers: chỉ đọc/ghi của mình
CREATE POLICY "teachers_own" ON teachers
  FOR ALL USING (id = auth.uid());

-- OCR jobs: chỉ của mình
CREATE POLICY "ocr_jobs_own" ON ocr_jobs
  FOR ALL USING (teacher_id = auth.uid());

-- Draft exams: chỉ của mình
CREATE POLICY "draft_exams_own" ON draft_exams
  FOR ALL USING (teacher_id = auth.uid());

-- Draft questions: thông qua quyền sở hữu draft_exam
CREATE POLICY "draft_questions_own" ON draft_questions
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM draft_exams
      WHERE draft_exams.id = draft_questions.draft_exam_id
        AND draft_exams.teacher_id = auth.uid()
    )
  );

-- Assignments: giáo viên CRUD của mình, học sinh read nếu là lớp của mình
CREATE POLICY "assignments_teacher_own" ON assignments
  FOR ALL USING (teacher_id = auth.uid());

CREATE POLICY "assignments_student_read" ON assignments
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM students
      WHERE students.id = auth.uid()
        AND (
          assignments.assigned_to = 'all'
          OR assignments.assigned_to = students.class_name
        )
    )
  );

-- Cho phép giáo viên INSERT vào exams và questions (khi publish)
CREATE POLICY "exams_teacher_insert" ON exams
  FOR INSERT WITH CHECK (
    EXISTS (SELECT 1 FROM teachers WHERE id = auth.uid())
  );

CREATE POLICY "questions_teacher_insert" ON questions
  FOR INSERT WITH CHECK (
    EXISTS (SELECT 1 FROM teachers WHERE id = auth.uid())
  );

-- ================================================================
-- Hướng dẫn tạo tài khoản giáo viên:
-- INSERT INTO teachers (id, full_name, email)
-- SELECT id, '<Họ tên>', '<email>'
-- FROM auth.users WHERE email = '<email giáo viên>';
-- ================================================================
