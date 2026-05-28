'use client'

import { useState, useEffect } from 'react'
import { useParams, useSearchParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import Header from '@/components/Header'
import Footer from '@/components/Footer'
import QuestionCard from '@/components/QuestionCard'
import SectionNumber from '@/components/ui/SectionNumber'
import { createClient } from '@/lib/supabase'
import type { Question, AnswerMap } from '@/lib/types'

function scoreLabel(score: number) {
  if (score >= 8) return { label: 'Xuất sắc', color: 'text-moss' }
  if (score >= 6.5) return { label: 'Tốt', color: 'text-moss' }
  if (score >= 5) return { label: 'Đạt yêu cầu', color: 'text-sun' }
  return { label: 'Cần cố gắng', color: 'text-ember' }
}

export default function ResultPage() {
  const router = useRouter()
  const { id } = useParams<{ id: string }>()
  const searchParams = useSearchParams()
  const subId = searchParams.get('sub')
  const supabase = createClient()

  const [questions, setQuestions] = useState<Question[]>([])
  const [answers, setAnswers] = useState<AnswerMap>({})
  const [score, setScore] = useState(0)
  const [correctCount, setCorrectCount] = useState(0)
  const [totalQuestions, setTotalQuestions] = useState(0)
  const [timeTaken, setTimeTaken] = useState(0)
  const [loading, setLoading] = useState(true)
  const [showReview, setShowReview] = useState(false)

  useEffect(() => {
    async function load() {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) { router.push('/login'); return }

      const { data: qs } = await supabase
        .from('questions')
        .select('id, exam_id, subject_id, topic_id, question_number, content, question_type, level, options, correct_answer, has_formula, has_image')
        .eq('exam_id', id)
        .eq('is_hidden', false)
        .order('question_number')
      if (qs) setQuestions(qs as Question[])

      if (subId) {
        const { data: sub } = await supabase
          .from('exam_submissions')
          .select('score, correct_count, total_questions, time_taken')
          .eq('id', subId)
          .single()
        if (sub) {
          setScore(sub.score ?? 0)
          setCorrectCount(sub.correct_count)
          setTotalQuestions(sub.total_questions)
          setTimeTaken(sub.time_taken ?? 0)
        }
        const { data: studentAnswers } = await supabase
          .from('student_answers')
          .select('question_id, answer')
          .eq('submission_id', subId)
        if (studentAnswers) {
          const map: AnswerMap = {}
          studentAnswers.forEach((a: { question_id: number; answer: string | null }) => {
            if (a.answer) map[a.question_id] = a.answer
          })
          setAnswers(map)
        }
      } else {
        const raw = sessionStorage.getItem(`exam_result_${id}`)
        if (raw) {
          const data = JSON.parse(raw)
          setAnswers(data.answers || {})
          setScore(data.score || 0)
          setCorrectCount(data.correctCount || 0)
          setTotalQuestions(data.totalQuestions || 0)
          setTimeTaken(data.timeTaken || 0)
        }
      }
      setLoading(false)
    }
    load()
  }, [id, subId, router, supabase])

  const mins = Math.floor(timeTaken / 60)
  const secs = timeTaken % 60
  const pct = totalQuestions > 0 ? Math.round((correctCount / totalQuestions) * 100) : 0
  const { label: scoreLbl, color: scoreCol } = scoreLabel(score)

  if (loading) {
    return (
      <div className="flex flex-col min-h-screen">
        <Header />
        <div className="flex-1 flex items-center justify-center">
          <p className="font-display text-3xl text-ink-50 italic">Đang tải kết quả…</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col min-h-screen">
      <Header />

      <main className="flex-1">
        {/* Hero score */}
        <section className="max-w-4xl mx-auto px-6 sm:px-10 pt-16 sm:pt-24 pb-16 text-center">
          <SectionNumber n={1} label="Kết quả bài thi" className="justify-center" />

          <p className="mt-12 text-xs tracking-label text-ink-50">Điểm số của bạn</p>
          <p className="font-display text-[120px] sm:text-[180px] leading-none mt-4 text-ink">
            {score.toFixed(1)}
          </p>
          <p className={`mt-4 font-display text-2xl italic ${scoreCol}`}>{scoreLbl}.</p>

          {/* Stats prose */}
          <div className="mt-16 font-display text-2xl sm:text-3xl text-ink-70 leading-relaxed max-w-2xl mx-auto">
            Bạn đã trả lời đúng <em className="italic text-ink">{correctCount} / {totalQuestions}</em> câu,
            đạt tỉ lệ <em className="italic text-ink">{pct}%</em>,
            trong <em className="italic text-ink">{mins} phút {String(secs).padStart(2, '0')} giây</em>.
          </div>

          {/* Score bar */}
          <div className="mt-12 max-w-md mx-auto">
            <div className="h-px bg-line relative">
              <div
                className={`absolute top-0 left-0 h-px ${
                  pct >= 80 ? 'bg-moss' : pct >= 65 ? 'bg-moss-soft' : pct >= 50 ? 'bg-sun' : 'bg-ember'
                }`}
                style={{ width: `${pct}%` }}
              />
              <span
                className="absolute -top-7 text-xs tracking-label font-mono text-ink"
                style={{ left: `${pct}%`, transform: 'translateX(-50%)' }}
              >
                {pct}%
              </span>
            </div>
          </div>

          {/* Actions */}
          <div className="mt-16 flex items-center justify-center gap-8 flex-wrap">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 px-7 py-3.5 bg-ink text-paper text-sm tracking-label hover:bg-moss transition-colors"
            >
              Về thống kê <span aria-hidden>→</span>
            </Link>
            <Link href="/exams" className="text-sm tracking-label text-ink link-editorial">
              Làm đề khác
            </Link>
          </div>
        </section>

        {/* Review toggle */}
        {questions.length > 0 && (
          <section className="border-t border-line">
            <div className="max-w-4xl mx-auto px-6 sm:px-10 py-12">
              <button
                onClick={() => setShowReview(s => !s)}
                className="w-full flex items-center justify-between text-left py-4 group"
              >
                <span className="font-display text-2xl sm:text-3xl text-ink group-hover:italic transition-all">
                  Xem lại từng câu
                </span>
                <span className="text-2xl text-ink-50 group-hover:text-ink transition-colors">
                  {showReview ? '—' : '+'}
                </span>
              </button>

              {showReview && (
                <div className="mt-10 flex flex-col gap-12">
                  {questions.map((q, i) => (
                    <div key={q.id} className="border-t border-line pt-10">
                      <QuestionCard
                        question={q}
                        index={i}
                        selectedAnswer={answers[q.id]}
                        onAnswer={() => {}}
                        showResult
                        isPaperLayout={true}
                      />
                    </div>
                  ))}
                </div>
              )}
            </div>
          </section>
        )}
      </main>

      <Footer />
    </div>
  )
}
