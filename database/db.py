"""
database/db.py — Tất cả thao tác PostgreSQL
"""
import hashlib
import json
import logging
from contextlib import contextmanager
from typing import Optional

import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import config

logger = logging.getLogger(__name__)

# Connection pool
_pool: Optional[ThreadedConnectionPool] = None


def init_pool(min_conn: int = 1, max_conn: int = 10):
    global _pool
    _pool = ThreadedConnectionPool(min_conn, max_conn, dsn=config.DATABASE_URL)
    logger.info("Database pool initialized")


@contextmanager
def get_conn():
    """Context manager trả về connection từ pool."""
    if _pool is None:
        init_pool()
    conn = _pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)


def init_schema():
    """Chạy schema.sql để tạo bảng nếu chưa có."""
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        sql = f.read()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
    logger.info("Schema initialized successfully")


# ─── Sources ─────────────────────────────────────────────────────────────────

def upsert_source(name: str, base_url: str) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO sources (name, base_url)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
                RETURNING id
            """, (name, base_url))
            row = cur.fetchone()
            if row:
                return row[0]
            cur.execute("SELECT id FROM sources WHERE base_url = %s", (base_url,))
            return cur.fetchone()[0]


# ─── Subjects & Topics ───────────────────────────────────────────────────────

def get_subject_id(code: str) -> Optional[int]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM subjects WHERE code = %s", (code,))
            row = cur.fetchone()
            return row[0] if row else None


def get_or_create_topic(subject_id: int, name: str) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO topics (subject_id, name)
                VALUES (%s, %s)
                ON CONFLICT (subject_id, name) DO NOTHING
                RETURNING id
            """, (subject_id, name))
            row = cur.fetchone()
            if row:
                return row[0]
            cur.execute(
                "SELECT id FROM topics WHERE subject_id = %s AND name = %s",
                (subject_id, name)
            )
            return cur.fetchone()[0]


def seed_topics():
    """Seed toàn bộ topics từ config."""
    from config import TOPICS, SUBJECTS
    for key, topic_list in TOPICS.items():
        subject_info = SUBJECTS.get(key)
        if not subject_info:
            continue
        subject_id = get_subject_id(subject_info["code"])
        if not subject_id:
            continue
        for topic_name in topic_list:
            get_or_create_topic(subject_id, topic_name)
    logger.info("Topics seeded successfully")


# ─── Exams ───────────────────────────────────────────────────────────────────

def pdf_hash(pdf_path: str) -> str:
    sha256 = hashlib.sha256()
    with open(pdf_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def exam_exists(pdf_hash_val: str) -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM exams WHERE pdf_hash = %s", (pdf_hash_val,))
            return cur.fetchone() is not None


def insert_exam(
    title: str,
    year: int,
    exam_type: str,
    subject_id: Optional[int],
    source_id: Optional[int],
    source_url: str,
    pdf_path: str,
    pdf_hash_val: str,
    total_pages: int = 0,
) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO exams
                    (title, year, exam_type, subject_id, source_id,
                     source_url, pdf_path, pdf_hash, total_pages)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (pdf_hash) DO NOTHING
                RETURNING id
            """, (title, year, exam_type, subject_id, source_id,
                  source_url, pdf_path, pdf_hash_val, total_pages))
            row = cur.fetchone()
            if row:
                return row[0]
            cur.execute("SELECT id FROM exams WHERE pdf_hash = %s", (pdf_hash_val,))
            return cur.fetchone()[0]


def update_exam_ocr(exam_id: int, markdown: str, status: str = "done"):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE exams
                SET ocr_markdown = %s, ocr_status = %s, processed_at = NOW()
                WHERE id = %s
            """, (markdown, status, exam_id))


def get_pending_exams(limit: int = 50) -> list:
    """Trả về các exam chưa OCR."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("""
                SELECT id, pdf_path, title, year, subject_id
                FROM exams
                WHERE ocr_status = 'pending'
                ORDER BY created_at
                LIMIT %s
            """, (limit,))
            return [dict(r) for r in cur.fetchall()]


def get_ocr_done_exams(limit: int = 50) -> list:
    """Trả về exam đã OCR nhưng chưa phân loại."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("""
                SELECT e.id, e.ocr_markdown, e.title, e.year, e.subject_id
                FROM exams e
                WHERE e.ocr_status = 'done'
                  AND NOT EXISTS (
                    SELECT 1 FROM questions q WHERE q.exam_id = e.id
                  )
                ORDER BY e.created_at
                LIMIT %s
            """, (limit,))
            return [dict(r) for r in cur.fetchall()]


# ─── Questions ───────────────────────────────────────────────────────────────

def insert_question(
    exam_id: int,
    subject_id: Optional[int],
    topic_id: Optional[int],
    question_number: int,
    content: str,
    content_raw: str,
    question_type: str,
    level: str,
    level_confidence: float,
    options: Optional[dict],
    correct_answer: Optional[str],
    explanation: Optional[str],
    has_formula: bool,
    has_image: bool,
    has_table: bool,
    classification_meta: Optional[dict],
) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO questions (
                    exam_id, subject_id, topic_id, question_number,
                    content, content_raw, question_type,
                    level, level_confidence,
                    options, correct_answer, explanation,
                    has_formula, has_image, has_table,
                    classification_meta, classified_at
                ) VALUES (
                    %s,%s,%s,%s,
                    %s,%s,%s,
                    %s,%s,
                    %s,%s,%s,
                    %s,%s,%s,
                    %s, NOW()
                )
                RETURNING id
            """, (
                exam_id, subject_id, topic_id, question_number,
                content, content_raw, question_type,
                level, level_confidence,
                json.dumps(options, ensure_ascii=False) if options else None,
                correct_answer, explanation,
                has_formula, has_image, has_table,
                json.dumps(classification_meta, ensure_ascii=False) if classification_meta else None,
            ))
            return cur.fetchone()[0]


# ─── Statistics ──────────────────────────────────────────────────────────────

def get_stats() -> dict:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT COUNT(*) as total FROM exams")
            total_exams = cur.fetchone()["total"]

            cur.execute("SELECT COUNT(*) as total FROM questions")
            total_questions = cur.fetchone()["total"]

            cur.execute("""
                SELECT s.name, COUNT(q.id) as count
                FROM questions q
                JOIN subjects s ON q.subject_id = s.id
                GROUP BY s.name ORDER BY count DESC
            """)
            by_subject = {r["name"]: r["count"] for r in cur.fetchall()}

            cur.execute("""
                SELECT level, COUNT(*) as count
                FROM questions
                WHERE level IS NOT NULL
                GROUP BY level ORDER BY level
            """)
            by_level = {r["level"]: r["count"] for r in cur.fetchall()}

            return {
                "total_exams": total_exams,
                "total_questions": total_questions,
                "by_subject": by_subject,
                "by_level": by_level,
            }
