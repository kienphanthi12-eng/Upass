'use client'

import { useState, useEffect, useMemo } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import SectionNumber from '@/components/ui/SectionNumber'
import DisplayHeading from '@/components/ui/DisplayHeading'

interface Submission {
  id: string
  exam_id: number
  submitted_at: string
  time_taken: number | null
  score: number | null
  total_questions: number
  correct_count: number
  status: 'completed' | 'in_progress'
  exams?: {
    title: string
    display_title: string | null
    year: number
    exam_type: string
  }
}

interface StudentInfo {
  id: string
  full_name: string
  class_name: string | null
  student_code: string | null
  created_at: string
}

function formatTime(s: number | null) {
  if (!s) return '—'
  const m = Math.floor(s / 60)
  return `${m}p ${s % 60}s`
}

function formatDate(ts: string) {
  return new Date(ts).toLocaleString('vi-VN', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function scoreColor(s: number | null) {
  if (s === null) return 'text-ink-30'
  if (s >= 8) return 'text-moss'
  if (s >= 5) return 'text-sun'
  return 'text-ember'
}

export default function StudentDetailPage() {
  const { studentId } = useParams() as { studentId: string }
  const router = useRouter()
  
  const [student, setStudent] = useState<StudentInfo | null>(null)
  const [submissions, setSubmissions] = useState<Submission[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetch(`/api/teacher/students/${studentId}`)
      .then(r => r.json())
      .then(data => {
        if (data.error) {
          setError(data.error)
        } else {
          setStudent(data.student)
          setSubmissions(data.submissions)
        }
      })
      .catch(() => setError('Không thể tải thông tin học sinh'))
      .finally(() => setLoading(false))
  }, [studentId])

  const completed = useMemo(() => submissions.filter(s => s.status === 'completed'), [submissions])
  const inProgress = useMemo(() => submissions.filter(s => s.status === 'in_progress'), [submissions])
  
  const avgScore = useMemo(() => {
    return completed.length > 0
      ? (completed.reduce((sum, s) => sum + (s.score ?? 0), 0) / completed.length).toFixed(2)
      : '—'
  }, [completed])

  if (loading) {
    return (
      <div className="p-10 flex items-center justify-center h-64">
        <p className="font-display text-3xl text-ink-50 italic">Đang tải thông tin…</p>
      </div>
    )
  }

  if (error || !student) {
    return (
      <div className="p-10 max-w-6xl">
        <Link href="/teacher/students" className="text-sm tracking-label text-ink-50 link-editorial">
          ← Quay lại danh sách học sinh
        </Link>
        <p className="mt-8 border-l-2 border-ember pl-4 text-ember">{error || 'Không tìm thấy thông tin học sinh'}</p>
      </div>
    )
  }

  return (
    <div className="p-10 max-w-6xl">
      <div className="flex items-center gap-3 mb-6">
        <Link href="/teacher/students" className="text-sm tracking-label text-ink-50 link-editorial">
          Danh sách học sinh
        </Link>
        <span className="text-ink-30">·</span>
        <span className="text-xs tracking-label text-ink-50">Chi tiết học sinh</span>
      </div>

      <SectionNumber n={1} label="Hồ sơ học sinh" />
      <DisplayHeading size="lg" className="mt-6">
        {student.full_name}.
      </DisplayHeading>
      
      <div className="mt-6 flex flex-wrap gap-x-8 gap-y-2 text-sm text-ink-50">
        {student.student_code && (
          <p>Mã học sinh: <span className="font-mono text-ink font-semibold">{student.student_code}</span></p>
        )}
        <p>Lớp: <span className="text-ink font-semibold">{student.class_name ?? 'Chưa phân lớp'}</span></p>
        <p>Ngày đăng ký: <span className="text-ink font-semibold">{formatDate(student.created_at)}</span></p>
      </div>

      {!loading && !error && (
        <p className="mt-10 font-display text-xl sm:text-2xl text-ink-70 leading-relaxed max-w-3xl">
          Đã thực hiện <em className="italic text-ink">{submissions.length} đề thi</em>, 
          trong đó hoàn thành <em className="italic text-ink">{completed.length} đề</em>
          {inProgress.length > 0 && (
            <> và đang làm <em className="italic text-sun font-semibold"> {inProgress.length} đề</em></>
          )}
          , điểm TB chung <em className="italic text-ink">{avgScore}</em>.
        </p>
      )}

      <div className="mt-16">
        <SectionNumber n={2} label="Lịch sử làm bài" />
        {submissions.length === 0 ? (
          <p className="mt-6 text-base text-ink-50 italic font-display text-2xl border-t border-line pt-8">
            Chưa có lịch sử làm bài nào.
          </p>
        ) : (
          <div className="mt-6">
            <div className="grid grid-cols-12 gap-4 text-xs tracking-label text-ink-50 pb-3 border-b border-line">
              <span className="col-span-1">#</span>
              <span className="col-span-4">Đề thi</span>
              <span className="col-span-2 text-right">Trạng thái</span>
              <span className="col-span-1 text-right">Điểm</span>
              <span className="col-span-1 text-right">Đúng</span>
              <span className="col-span-1 text-right">Thời gian</span>
              <span className="col-span-2 text-right">Hành động</span>
            </div>
            {submissions.map((s, i) => (
              <div key={s.id} className="grid grid-cols-12 gap-4 py-4 border-b border-line items-baseline">
                <span className="col-span-1 text-xs font-mono text-ink-50">
                  ({String(i + 1).padStart(2, '0')})
                </span>
                <div className="col-span-4">
                  <p className="font-display text-lg text-ink font-semibold">
                    {s.exams?.title || 'Đề thi'}
                    {s.exams?.display_title && (
                      <span className="text-xs font-sans font-normal text-ink-30 ml-2">
                        ({s.exams.display_title})
                      </span>
                    )}
                  </p>
                  <p className="text-xs text-ink-30 mt-0.5">{s.exams?.year} · {s.exams?.exam_type}</p>
                </div>
                <span className={`col-span-2 text-right text-xs tracking-label font-bold ${
                  s.status === 'completed' ? 'text-moss' : 'text-sun animate-pulse'
                }`}>
                  {s.status === 'completed' ? 'Đã hoàn thành' : 'Đang làm...'}
                </span>
                <span className={`col-span-1 text-right font-display text-lg tabular-nums ${
                  s.status === 'completed' ? scoreColor(s.score) : 'text-ink-30'
                }`}>
                  {s.status === 'completed' ? s.score?.toFixed(2) : '—'}
                </span>
                <span className="col-span-1 text-right text-sm text-ink-70 tabular-nums">
                  {s.status === 'completed' ? `${s.correct_count}/${s.total_questions}` : '—'}
                </span>
                <span className="col-span-1 text-right text-sm text-ink-50 tabular-nums">
                  {s.status === 'completed' ? formatTime(s.time_taken) : '—'}
                </span>
                <div className="col-span-2 text-right">
                  {s.status === 'completed' ? (
                    <Link
                      href={`/teacher/submissions/${s.id}`}
                      className="text-sm tracking-label text-ink link-editorial font-semibold"
                    >
                      Chi tiết →
                    </Link>
                  ) : (
                    <span className="text-sm tracking-label text-ink-30">—</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
