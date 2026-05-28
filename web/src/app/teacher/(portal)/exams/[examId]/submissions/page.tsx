'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import SectionNumber from '@/components/ui/SectionNumber'
import DisplayHeading from '@/components/ui/DisplayHeading'

interface SubmissionRow {
  id: string
  student_id: string
  submitted_at: string
  time_taken: number | null
  score: number | null
  total_questions: number
  correct_count: number
  students?: { full_name: string; class_name: string | null; student_code: string | null }
}

function formatTime(s: number | null) {
  if (!s) return '—'
  const m = Math.floor(s / 60)
  return `${m}p ${s % 60}s`
}

function formatDate(ts: string) {
  return new Date(ts).toLocaleString('vi-VN', {
    day: '2-digit', month: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

function scoreColor(s: number | null) {
  if (s === null) return 'text-ink-30'
  if (s >= 8) return 'text-moss'
  if (s >= 5) return 'text-sun'
  return 'text-ember'
}

export default function SubmissionsPage() {
  const { examId } = useParams() as { examId: string }
  const [rows, setRows] = useState<SubmissionRow[]>([])
  const [loading, setLoading] = useState(true)
  const [exam, setExam] = useState<any>(null)

  useEffect(() => {
    Promise.all([
      fetch(`/api/teacher/exams/${examId}/submissions`).then(r => r.json()),
      fetch(`/api/exams/${examId}`).then(r => r.json()).catch(() => null),
    ]).then(([subs, examData]) => {
      setRows(Array.isArray(subs) ? subs : [])
      if (examData) setExam(examData)
      setLoading(false)
    })
  }, [examId])

  const avg = rows.length > 0
    ? (rows.reduce((s, r) => s + (r.score ?? 0), 0) / rows.length).toFixed(2)
    : null

  const pass = rows.filter(r => (r.score ?? 0) >= 5).length

  if (loading) {
    return (
      <div className="p-10 flex items-center justify-center h-64">
        <p className="font-display text-3xl text-ink-50 italic">Đang tải…</p>
      </div>
    )
  }

  return (
    <div className="p-10 max-w-6xl">
      <div className="flex items-center gap-3 mb-6">
        <Link href="/teacher/exams" className="text-sm tracking-label text-ink-50 link-editorial">
          ← Đề
        </Link>
        <span className="text-ink-30">·</span>
        <span className="text-xs tracking-label text-ink-50">Kết quả</span>
      </div>

      <SectionNumber n={1} label="Kết quả học sinh" />
      <DisplayHeading size="lg" className="mt-6">
        {exam?.title || exam?.display_title || 'Kết quả'}.
        {exam?.display_title && exam?.title && (
          <span className="block text-xl font-sans font-normal text-ink-30 mt-2">
            Mã đề hiển thị học sinh: {exam.display_title}
          </span>
        )}
      </DisplayHeading>

      {rows.length > 0 && (
        <p className="mt-8 font-display text-xl sm:text-2xl text-ink-70 leading-relaxed max-w-3xl">
          <em className="italic text-ink">{rows.length} lượt nộp</em>,
          điểm TB <em className="italic text-ink">{avg}</em>,
          <em className="italic text-ink"> {pass} học sinh</em> đạt (≥ 5đ).
        </p>
      )}

      <div className="mt-16">
        {rows.length === 0 ? (
          <p className="text-center py-24 border-t border-line font-display text-3xl text-ink-50 italic">
            Chưa có học sinh nộp bài.
          </p>
        ) : (
          <div>
            <div className="grid grid-cols-12 gap-4 text-xs tracking-label text-ink-50 pb-3 border-b border-line">
              <span className="col-span-1">#</span>
              <span className="col-span-3">Học sinh</span>
              <span className="col-span-1">Lớp</span>
              <span className="col-span-2 text-right">Điểm</span>
              <span className="col-span-1 text-right">Đúng</span>
              <span className="col-span-1 text-right">Thời gian</span>
              <span className="col-span-1 text-right">Nộp lúc</span>
              <span className="col-span-2 text-right">Hành động</span>
            </div>
            {rows.map((r, i) => (
              <div key={r.id} className="grid grid-cols-12 gap-4 py-4 border-b border-line items-baseline">
                <span className="col-span-1 text-xs font-mono text-ink-50">
                  ({String(i + 1).padStart(2, '0')})
                </span>
                <div className="col-span-3">
                  <Link href={`/teacher/students/${r.student_id}`} className="hover:underline hover:italic">
                    <p className="font-display text-xl text-ink inline-block">{r.students?.full_name ?? 'Ẩn danh'}</p>
                  </Link>
                </div>
                <span className="col-span-1 text-sm text-ink-50">
                  {r.students?.class_name ?? '—'}
                </span>
                <span className={`col-span-2 text-right text-xl font-display tabular-nums ${scoreColor(r.score)}`}>
                  {r.score?.toFixed(2) ?? '—'}
                </span>
                <span className="col-span-1 text-right text-sm text-ink-70 tabular-nums">
                  {r.correct_count}/{r.total_questions}
                </span>
                <span className="col-span-1 text-right text-sm text-ink-50 tabular-nums">
                  {formatTime(r.time_taken)}
                </span>
                <span className="col-span-1 text-right text-xs text-ink-50">
                  {formatDate(r.submitted_at)}
                </span>
                <div className="col-span-2 text-right">
                  <Link
                    href={`/teacher/submissions/${r.id}`}
                    className="text-sm tracking-label text-ink link-editorial font-semibold"
                  >
                    Chi tiết →
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
