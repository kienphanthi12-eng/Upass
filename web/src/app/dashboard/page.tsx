'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import Header from '@/components/Header'
import Footer from '@/components/Footer'
import SectionNumber from '@/components/ui/SectionNumber'
import DisplayHeading from '@/components/ui/DisplayHeading'
import ScrollReveal from '@/components/ui/ScrollReveal'
import { createClient } from '@/lib/supabase'
import type { ExamSubmission, Student } from '@/lib/types'
import { examDisplayName } from '@/lib/types'

function formatDate(ts: string) {
  return new Date(ts).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })
}
function formatTime(s: number) {
  const m = Math.floor(s / 60)
  return `${m}p ${s % 60}s`
}

function scoreColor(s: number) {
  if (s >= 8) return 'text-moss'
  if (s >= 6.5) return 'text-moss-soft'
  if (s >= 5) return 'text-sun'
  return 'text-ember'
}

export default function DashboardPage() {
  const router = useRouter()
  const supabase = createClient()
  interface TopicStat {
    topicId: number
    topicName: string
    total: number
    correct: number
    accuracy: number
  }

  const [student, setStudent] = useState<Student | null>(null)
  const [submissions, setSubmissions] = useState<ExamSubmission[]>([])
  const [topicStats, setTopicStats] = useState<TopicStat[]>([])
  const [filterYear, setFilterYear] = useState<string>('all')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) { router.push('/login'); return }

      const [studentRes, subRes] = await Promise.all([
        supabase.from('students').select('*').eq('id', user.id).single(),
        supabase
          .from('exam_submissions')
          .select('id, student_id, exam_id, submitted_at, time_taken, score, total_questions, correct_count, status, exams(id, title, display_title, year, exam_type)')
          .eq('student_id', user.id)
          .eq('status', 'completed')
          .order('submitted_at', { ascending: false })
          .limit(20),
      ])

      if (studentRes.data) setStudent(studentRes.data as Student)
      if (subRes.data) {
        const subs = subRes.data as unknown as ExamSubmission[]
        setSubmissions(subs)

        const subIds = subs.map(s => s.id)
        if (subIds.length > 0) {
          const { data: answersData } = await supabase
            .from('student_answers')
            .select('is_correct, questions(id, topic_id, topics(id, name))')
            .in('submission_id', subIds)

          if (answersData) {
            const statsMap = new Map<number, { topicId: number; topicName: string; total: number; correct: number }>()

            answersData.forEach(row => {
              const q = row.questions as any
              if (!q || !q.topics) return
              const topicId = q.topic_id
              const topicName = q.topics.name

              const existing = statsMap.get(topicId)
              if (existing) {
                existing.total++
                if (row.is_correct) existing.correct++
              } else {
                statsMap.set(topicId, {
                  topicId,
                  topicName,
                  total: 1,
                  correct: row.is_correct ? 1 : 0
                })
              }
            })

            const stats = Array.from(statsMap.values()).map(stat => ({
              ...stat,
              accuracy: Math.round((stat.correct / stat.total) * 100)
            }))

            setTopicStats(stats)
          }
        }
      }
      setLoading(false)
    }
    load()
  }, [])

  const years = [...new Set(submissions.map(s => s.exams?.year).filter(Boolean))].sort((a, b) => b! - a!).map(String)
  const filtered = filterYear === 'all' ? submissions : submissions.filter(s => String(s.exams?.year) === filterYear)

  const totalExams = submissions.length
  const avgScore = totalExams > 0
    ? submissions.reduce((s, r) => s + (r.score ?? 0), 0) / totalExams
    : 0
  const totalCorrect = submissions.reduce((s, r) => s + r.correct_count, 0)
  const totalQ = submissions.reduce((s, r) => s + r.total_questions, 0)
  const accuracy = totalQ > 0 ? Math.round((totalCorrect / totalQ) * 100) : 0
  const bestScore = totalExams > 0 ? Math.max(...submissions.map(s => s.score ?? 0)) : 0

  if (loading) {
    return (
      <div className="flex flex-col min-h-screen">
        <Header />
        <div className="flex-1 flex items-center justify-center">
          <p className="font-display text-3xl text-ink-50 italic">Đang tải…</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col min-h-screen">
      <Header />

      <main className="flex-1">
        {/* Greeting */}
        <section className="max-w-7xl mx-auto px-6 sm:px-10 pt-16 sm:pt-24 pb-16">
          <ScrollReveal>
            <SectionNumber n={1} label="Thống kê cá nhân" />
          </ScrollReveal>
          <ScrollReveal delay={0.08}>
            <DisplayHeading size="xl" className="mt-6 max-w-4xl leading-tight">
              Xin chào, <em className="italic">{student?.full_name || 'bạn'}</em>.
            </DisplayHeading>
          </ScrollReveal>
          {student?.class_name && (
            <ScrollReveal delay={0.15}>
              <p className="mt-4 text-base text-ink-50">Lớp {student.class_name}</p>
            </ScrollReveal>
          )}

          {/* Inline prose stats */}
          {totalExams > 0 ? (
            <ScrollReveal delay={0.22}>
              <p className="mt-12 font-display text-2xl sm:text-3xl text-ink-70 leading-relaxed max-w-3xl">
                Bạn đã hoàn thành <em className="italic text-ink">{totalExams} đề thi</em>,
                điểm trung bình <em className="italic text-ink">{avgScore.toFixed(2)}</em>,
                tỉ lệ đúng <em className="italic text-ink">{accuracy}%</em>,
                điểm cao nhất <em className="italic text-ink">{bestScore.toFixed(1)}</em>.
              </p>
            </ScrollReveal>
          ) : (
            <ScrollReveal delay={0.22}>
              <p className="mt-12 font-display text-2xl sm:text-3xl text-ink-70 leading-relaxed max-w-3xl">
                Bạn chưa làm đề nào. <em className="italic text-ink">Bắt đầu</em> ngay nhé.
              </p>
            </ScrollReveal>
          )}

          <ScrollReveal delay={0.3}>
            <div className="mt-10 flex items-center gap-6 flex-wrap">
              <Link
                href="/exams"
                className="inline-flex items-center gap-2 px-7 py-3.5 bg-ink text-paper text-sm tracking-label hover:bg-moss transition-colors"
              >
                Làm đề thi mới <span aria-hidden>→</span>
              </Link>
              <Link href="/practice" className="text-sm tracking-label text-ink link-editorial">
                Luyện tập
              </Link>
            </div>
          </ScrollReveal>
        </section>

        {/* Topic Analysis */}
        {topicStats.length > 0 && (
          <section className="border-t border-line">
            <div className="max-w-7xl mx-auto px-6 sm:px-10 py-16 sm:py-20">
              <ScrollReveal>
                <SectionNumber n={2} label="Phân tích chuyên đề" />
              </ScrollReveal>
              <ScrollReveal delay={0.08}>
                <h2 className="font-display text-3xl sm:text-4xl text-ink mt-4 mb-10">
                  Hiệu suất theo <em className="italic">chuyên đề</em>.
                </h2>
              </ScrollReveal>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-12 sm:gap-16">
                {/* Needs Improvement */}
                <div>
                  <h3 className="font-display text-xl text-amber-600 mb-6 flex items-center gap-2 font-semibold">
                    <span>⚠️</span> Cần cải thiện (Dưới 70%)
                  </h3>
                  {topicStats.filter(t => t.accuracy < 70).length === 0 ? (
                    <p className="text-sm text-ink-50 italic">Tuyệt vời! Bạn không có chuyên đề nào dưới 70%.</p>
                  ) : (
                    <div className="space-y-6">
                      {topicStats
                        .filter(t => t.accuracy < 70)
                        .sort((a, b) => a.accuracy - b.accuracy)
                        .map(t => (
                          <div key={t.topicId} className="space-y-2">
                            <div className="flex justify-between text-sm">
                              <span className="font-medium text-ink">{t.topicName}</span>
                              <span className="font-mono text-amber-600 font-bold">{t.accuracy}% ({t.correct}/{t.total} câu)</span>
                            </div>
                            <div className="h-2 bg-line rounded-full overflow-hidden">
                              <div 
                                className="h-full bg-amber-500 rounded-full transition-all duration-500" 
                                style={{ width: `${t.accuracy}%` }}
                              />
                            </div>
                          </div>
                        ))}
                    </div>
                  )}
                </div>

                {/* Strengths */}
                <div>
                  <h3 className="font-display text-xl text-moss mb-6 flex items-center gap-2 font-semibold">
                    <span>✓</span> Điểm mạnh (Từ 70% trở lên)
                  </h3>
                  {topicStats.filter(t => t.accuracy >= 70).length === 0 ? (
                    <p className="text-sm text-ink-50 italic">Hãy làm thêm bài để xây dựng các chuyên đề thế mạnh của bạn.</p>
                  ) : (
                    <div className="space-y-6">
                      {topicStats
                        .filter(t => t.accuracy >= 70)
                        .sort((a, b) => b.accuracy - a.accuracy)
                        .map(t => (
                          <div key={t.topicId} className="space-y-2">
                            <div className="flex justify-between text-sm">
                              <span className="font-medium text-ink">{t.topicName}</span>
                              <span className="font-mono text-moss font-bold">{t.accuracy}% ({t.correct}/{t.total} câu)</span>
                            </div>
                            <div className="h-2 bg-line rounded-full overflow-hidden">
                              <div 
                                className="h-full bg-moss rounded-full transition-all duration-500" 
                                style={{ width: `${t.accuracy}%` }}
                              />
                            </div>
                          </div>
                        ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </section>
        )}

        {/* History */}
        <section className="border-t border-line">
          <div className="max-w-7xl mx-auto px-6 sm:px-10 py-16 sm:py-20">
            <div className="flex items-end justify-between gap-4 flex-wrap mb-10">
              <div>
                <SectionNumber n={topicStats.length > 0 ? 3 : 2} label="Lịch sử làm bài" />
                <h2 className="font-display text-3xl sm:text-4xl text-ink mt-4">
                  {filtered.length} bài gần đây.
                </h2>
              </div>

              {years.length > 1 && (
                <div className="flex items-center gap-4">
                  <span className="text-xs tracking-label text-ink-50">Năm</span>
                  <button
                    onClick={() => setFilterYear('all')}
                    className={`text-sm tracking-label transition-colors ${
                      filterYear === 'all' ? 'text-ink' : 'text-ink-30 hover:text-ink'
                    }`}
                  >Tất cả</button>
                  {years.map(y => (
                    <button
                      key={y}
                      onClick={() => setFilterYear(y)}
                      className={`text-sm tracking-label transition-colors ${
                        filterYear === y ? 'text-ink' : 'text-ink-30 hover:text-ink'
                      }`}
                    >{y}</button>
                  ))}
                </div>
              )}
            </div>

            {filtered.length === 0 ? (
              <div className="text-center py-24 border-t border-line">
                <p className="font-display text-3xl text-ink-50 italic">Chưa có bài thi nào.</p>
                <Link
                  href="/exams"
                  className="mt-6 inline-flex items-center gap-2 text-sm tracking-label text-ink link-editorial"
                >
                  Bắt đầu làm đề →
                </Link>
              </div>
            ) : (
              <ul>
                {filtered.map((sub, i) => {
                  const sc = sub.score ?? 0
                  return (
                    <li key={sub.id}>
                      <Link
                        href={`/exams/${sub.exam_id}/result?sub=${sub.id}`}
                        className="group block border-t border-line py-6 hover:bg-paper-soft transition-colors -mx-6 sm:-mx-10 px-6 sm:px-10"
                      >
                        <div className="grid grid-cols-12 gap-4 items-baseline">
                          <span className="col-span-2 sm:col-span-1 text-xs tracking-label text-ink-50 font-mono">
                            ({String(i + 1).padStart(2, '0')})
                          </span>
                          <div className="col-span-7 sm:col-span-6">
                            <h3 className="font-display text-xl sm:text-2xl text-ink leading-snug group-hover:italic transition-all">
                              {examDisplayName(sub.exams) || `Đề thi #${sub.exam_id}`}
                            </h3>
                            <p className="mt-1 text-xs tracking-label text-ink-50">
                              {sub.correct_count}/{sub.total_questions} câu
                              {sub.time_taken ? ` · ${formatTime(sub.time_taken)}` : ''}
                              {' · '}{formatDate(sub.submitted_at)}
                            </p>
                          </div>
                          <div className="col-span-2 sm:col-span-4 text-right">
                            <span className={`font-display text-2xl sm:text-3xl ${scoreColor(sc)}`}>
                              {sc.toFixed(1)}
                            </span>
                          </div>
                          <span className="col-span-1 text-right text-ink-30 group-hover:text-ink transition-colors">
                            →
                          </span>
                        </div>
                      </Link>
                    </li>
                  )
                })}
                <li className="border-t border-line" />
              </ul>
            )}
          </div>
        </section>
      </main>

      <Footer />
    </div>
  )
}
