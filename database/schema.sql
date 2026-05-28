-- ============================================================
--  THPT Exam Tool — PostgreSQL Schema
--  Chạy: psql -U postgres -d thpt_exams -f schema.sql
-- ============================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- Full-text search on Vietnamese

-- ─── Môn học ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS subjects (
    id         SERIAL PRIMARY KEY,
    code       VARCHAR(20) UNIQUE NOT NULL,   -- TOAN, LY, HOA, ...
    name       VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ─── Chủ đề trong từng môn ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS topics (
    id         SERIAL PRIMARY KEY,
    subject_id INT NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    name       VARCHAR(300) NOT NULL,
    parent_id  INT REFERENCES topics(id),    -- hỗ trợ topic lồng nhau
    UNIQUE (subject_id, name)
);

-- ─── Nguồn website đã scrape ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sources (
    id             SERIAL PRIMARY KEY,
    name           VARCHAR(200) NOT NULL,
    base_url       TEXT NOT NULL,
    last_scraped   TIMESTAMP,
    total_found    INT DEFAULT 0
);

-- ─── Đề thi (một file PDF) ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS exams (
    id             SERIAL PRIMARY KEY,
    title          VARCHAR(1000),
    year           INT,
    exam_type      VARCHAR(100),       -- THPT_QG, GK, CK, THU, MINHOA, ...
    subject_id     INT REFERENCES subjects(id),
    source_id      INT REFERENCES sources(id),
    source_url     TEXT,
    pdf_path       TEXT,               -- đường dẫn file PDF local
    pdf_hash       VARCHAR(64),        -- SHA256 để tránh trùng lặp
    ocr_status     VARCHAR(20) DEFAULT 'pending',  -- pending/processing/done/error
    ocr_markdown   TEXT,               -- kết quả raw từ MinerU
    total_pages    INT,
    created_at     TIMESTAMP DEFAULT NOW(),
    processed_at   TIMESTAMP,
    UNIQUE (pdf_hash)
);

-- ─── Câu hỏi (đã tách từ đề thi) ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS questions (
    id               SERIAL PRIMARY KEY,
    exam_id          INT NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
    subject_id       INT REFERENCES subjects(id),
    topic_id         INT REFERENCES topics(id),
    question_number  INT,

    -- Nội dung câu hỏi (Markdown với LaTeX cho công thức)
    content          TEXT NOT NULL,
    content_raw      TEXT,             -- text thuần trước khi format

    -- Loại câu
    question_type    VARCHAR(50),      -- trac_nghiem / tu_luan / dung_sai

    -- Mức độ
    level            VARCHAR(50),      -- Nhận biết / Thông hiểu / Vận dụng / Vận dụng cao
    level_confidence FLOAT,            -- độ tin cậy của DeepSeek (0-1)

    -- Đáp án (trắc nghiệm)
    options          JSONB,            -- {"A": "...", "B": "...", "C": "...", "D": "..."}
    correct_answer   VARCHAR(10),      -- "A", "B", "C", "D" hoặc text tự luận

    -- Giải thích / lời giải
    explanation      TEXT,

    -- Flags media
    has_formula      BOOLEAN DEFAULT FALSE,
    has_image        BOOLEAN DEFAULT FALSE,
    has_table        BOOLEAN DEFAULT FALSE,

    -- Metadata từ DeepSeek
    classification_meta  JSONB,       -- full response từ AI

    -- Timestamps
    created_at       TIMESTAMP DEFAULT NOW(),
    classified_at    TIMESTAMP
);

-- ─── Indexes ─────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_questions_subject   ON questions(subject_id);
CREATE INDEX IF NOT EXISTS idx_questions_topic     ON questions(topic_id);
CREATE INDEX IF NOT EXISTS idx_questions_level     ON questions(level);
CREATE INDEX IF NOT EXISTS idx_questions_type      ON questions(question_type);
CREATE INDEX IF NOT EXISTS idx_questions_exam      ON questions(exam_id);
CREATE INDEX IF NOT EXISTS idx_exams_year          ON exams(year);
CREATE INDEX IF NOT EXISTS idx_exams_subject       ON exams(subject_id);
CREATE INDEX IF NOT EXISTS idx_exams_ocr_status    ON exams(ocr_status);

-- Full-text search cho nội dung câu hỏi (tiếng Việt)
CREATE INDEX IF NOT EXISTS idx_questions_content_trgm
    ON questions USING gin(content gin_trgm_ops);

-- ─── View tổng hợp ────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW v_questions_full AS
SELECT
    q.id,
    q.question_number,
    q.content,
    q.question_type,
    q.level,
    q.level_confidence,
    q.options,
    q.correct_answer,
    q.has_formula,
    q.has_image,
    q.has_table,
    s.name  AS subject_name,
    s.code  AS subject_code,
    t.name  AS topic_name,
    e.title AS exam_title,
    e.year  AS exam_year,
    e.exam_type,
    src.name AS source_name
FROM questions q
LEFT JOIN subjects s   ON q.subject_id = s.id
LEFT JOIN topics t     ON q.topic_id   = t.id
LEFT JOIN exams e      ON q.exam_id    = e.id
LEFT JOIN sources src  ON e.source_id  = src.id;

-- ─── Seed dữ liệu môn học ────────────────────────────────────────────────────
INSERT INTO subjects (code, name) VALUES
    ('TOAN',  'Toán'),
    ('LY',    'Vật Lý'),
    ('HOA',   'Hóa Học'),
    ('SINH',  'Sinh Học'),
    ('VAN',   'Ngữ Văn'),
    ('SU',    'Lịch Sử'),
    ('DIA',   'Địa Lý'),
    ('GDCD',  'GDCD'),
    ('ANH',   'Tiếng Anh'),
    ('TIN',   'Tin Học'),
    ('CN',    'Công Nghệ')
ON CONFLICT (code) DO NOTHING;
