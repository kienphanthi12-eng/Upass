'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import SectionNumber from '@/components/ui/SectionNumber'
import DisplayHeading from '@/components/ui/DisplayHeading'
import QuestionCard from '@/components/QuestionCard'

interface SubmissionDetail {
  id: string
  student_id: string
  exam_id: number
  submitted_at: string
  time_taken: number | null
  score: number | null
  total_questions: number
  correct_count: number
  status: 'completed' | 'in_progress'
  exams?: {
    id: number
    title: string
    display_title: string | null
    year: number
    exam_type: string
  }
  students?: {
    id: string
    full_name: string
    class_name: string | null
    student_code: string | null
  }
}

interface Question {
  id: number
  exam_id: number
  subject_id: number
  topic_id: number | null
  question_number: number
  content: string
  question_type: 'trac_nghiem' | 'dung_sai' | 'tu_luan'
  level: string
  options: Record<string, string> | null
  correct_answer: string | null
  has_formula: boolean
  has_image: boolean
}

interface AnswerDetail {
  answer: string | null
  is_correct: boolean | null
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

export default function SubmissionDetailPage() {
  const { submissionId } = useParams() as { submissionId: string }
  const router = useRouter()

  const [submission, setSubmission] = useState<SubmissionDetail | null>(null)
  const [questions, setQuestions] = useState<Question[]>([])
  const [answers, setAnswers] = useState<Record<number, AnswerDetail>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetch(`/api/teacher/submissions/${submissionId}`)
      .then(r => r.json())
      .then(data => {
        if (data.error) {
          setError(data.error)
        } else {
          setSubmission(data.submission)
          setQuestions(data.questions)
          setAnswers(data.answers)
        }
      })
      .catch(() => setError('Không thể tải chi tiết bài làm'))
      .finally(() => setLoading(false))
  }, [submissionId])

  if (loading) {
    return (
      <div className="p-10 flex items-center justify-center h-64">
        <p className="font-display text-3xl text-ink-50 italic">Đang tải chi tiết bài làm…</p>
      </div>
    )
  }

  if (error || !submission) {
    return (
      <div className="p-10 max-w-6xl">
        <button onClick={() => router.back()} className="text-sm tracking-label text-ink-50 link-editorial">
          ← Quay lại
        </button>
        <p className="mt-8 border-l-2 border-ember pl-4 text-ember">{error || 'Không tìm thấy thông tin bài làm'}</p>
      </div>
    )
  }

  const mins = submission.time_taken ? Math.floor(submission.time_taken / 60) : 0
  const secs = submission.time_taken ? submission.time_taken % 60 : 0
  const pct = submission.total_questions > 0 ? Math.round((submission.correct_count / submission.total_questions) * 100) : 0

  return (
    <div className="p-10 max-w-6xl">
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => router.back()} className="text-sm tracking-label text-ink-50 link-editorial">
          ← Quay lại
        </button>
        <span className="text-ink-30">·</span>
        <span className="text-xs tracking-label text-ink-50">Chi tiết bài làm</span>
      </div>

      <SectionNumber n={1} label="Bài làm của học sinh" />
      <DisplayHeading size="lg" className="mt-6 font-display">
        {submission.students?.full_name}.
      </DisplayHeading>

      <div className="mt-6 flex flex-wrap gap-x-8 gap-y-2 text-sm text-ink-50 border-b border-line pb-6">
        <p>Lớp: <span className="text-ink font-semibold">{submission.students?.class_name ?? '—'}</span></p>
        {submission.students?.student_code && (
          <p>Mã HS: <span className="font-mono text-ink font-semibold">{submission.students?.student_code}</span></p>
        )}
        <p>Đề thi: <span className="text-ink font-semibold">
          {submission.exams?.title}
          {submission.exams?.display_title && ` (${submission.exams.display_title})`}
        </span></p>
        <p>Nộp lúc: <span className="text-ink font-semibold">{formatDate(submission.submitted_at)}</span></p>
      </div>

      {/* Hero score */}
      <section className="py-12 text-center">
        <p className="text-xs tracking-label text-ink-50">Điểm số đạt được</p>
        <p className={`font-display text-[100px] sm:text-[140px] leading-none mt-4 font-bold ${scoreColor(submission.score)}`}>
          {submission.score?.toFixed(2) ?? '—'}
        </p>
        
        <div className="mt-10 font-display text-xl sm:text-2xl text-ink-70 leading-relaxed max-w-2xl mx-auto">
          Đúng <em className="italic text-ink">{submission.correct_count} / {submission.total_questions}</em> câu,
          đạt tỉ lệ <em className="italic text-ink">{pct}%</em>,
          làm bài trong <em className="italic text-ink">{mins} phút {secs} giây</em>.
        </div>
      </section>

      {/* Review Section */}
      {questions.length > 0 && (
        <section className="border-t border-line mt-6 pt-10">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-center justify-between mb-8">
              <h2 className="font-display text-2xl sm:text-3xl text-ink">
                Xem lại từng câu
              </h2>
            </div>

            <div className="flex flex-col gap-12">
              {questions.map((q, i) => (
                <div key={q.id} className="border-t border-line pt-10 first:border-0 first:pt-0">
                  <QuestionCard
                    question={q as any}
                    index={i}
                    selectedAnswer={answers[q.id]?.answer ?? undefined}
                    onAnswer={() => {}}
                    showResult
                  />
                </div>
              ))}
            </div>
          </div>
        </section>
      )}
    </div>
  )
}
