'use client'

import { useState, useEffect } from 'react'
import Header from '@/components/Header'
import Footer from '@/components/Footer'
import SectionNumber from '@/components/ui/SectionNumber'
import DisplayHeading from '@/components/ui/DisplayHeading'
import ScrollReveal from '@/components/ui/ScrollReveal'
import { createClient } from '@/lib/supabase'

interface LeaderboardEntry {
  student_id: string
  full_name: string
  class_name: string | null
  exam_count: number
  avg_score: number
  best_score: number
  total_correct: number
  total_questions: number
}

export default function LeaderboardPage() {
  const supabase = createClient()
  const [entries, setEntries] = useState<LeaderboardEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [currentUserId, setCurrentUserId] = useState<string | null>(null)
  const [filter, setFilter] = useState<'avg_score' | 'exam_count' | 'best_score'>('avg_score')

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => setCurrentUserId(data.user?.id ?? null))
  }, [])

  useEffect(() => {
    async function load() {
      setLoading(true)
      const { data } = await supabase
        .from('exam_submissions')
        .select('student_id, score, correct_count, total_questions, students(id, full_name, class_name)')
        .eq('status', 'completed')

      if (!data) { setLoading(false); return }

      const map = new Map<string, LeaderboardEntry>()
      for (const row of data) {
        const s = row.students as unknown as { id: string; full_name: string; class_name: string | null } | null
        if (!s) continue
        const existing = map.get(row.student_id)
        if (existing) {
          existing.exam_count++
          existing.avg_score += (row.score ?? 0)
          existing.best_score = Math.max(existing.best_score, row.score ?? 0)
          existing.total_correct += row.correct_count
          existing.total_questions += row.total_questions
        } else {
          map.set(row.student_id, {
            student_id: row.student_id,
            full_name: s.full_name,
            class_name: s.class_name,
            exam_count: 1,
            avg_score: row.score ?? 0,
            best_score: row.score ?? 0,
            total_correct: row.correct_count,
            total_questions: row.total_questions,
          })
        }
      }

      const list = Array.from(map.values()).map(e => ({
        ...e,
        avg_score: e.exam_count > 0 ? e.avg_score / e.exam_count : 0,
      }))
      setEntries(list)
      setLoading(false)
    }
    load()
  }, [])

  const sorted = [...entries].sort((a, b) => b[filter] - a[filter])

  const filterLabels = {
    avg_score: 'Điểm trung bình',
    best_score: 'Điểm cao nhất',
    exam_count: 'Số bài đã làm',
  }

  return (
    <div className="flex flex-col min-h-screen">
      <Header />

      <main className="flex-1">
        <section className="max-w-5xl mx-auto px-6 sm:px-10 pt-16 sm:pt-24 pb-12">
          <ScrollReveal>
            <SectionNumber n={1} label="Vinh danh" />
          </ScrollReveal>
          <ScrollReveal delay={0.08}>
            <DisplayHeading size="xl" className="mt-6">
              Bảng <em className="italic">xếp hạng</em>.
            </DisplayHeading>
          </ScrollReveal>
          <ScrollReveal delay={0.15}>
            <p className="mt-6 text-base text-ink-50">
              Xếp hạng học sinh theo kết quả làm bài trên U-PASS.
            </p>
          </ScrollReveal>

          {/* Filter row */}
          <div className="mt-10 flex flex-wrap items-center gap-6">
            <span className="text-xs tracking-label text-ink-50">Sắp xếp theo</span>
            {(Object.keys(filterLabels) as Array<keyof typeof filterLabels>).map(val => (
              <button
                key={val}
                onClick={() => setFilter(val)}
                className={`text-sm tracking-label transition-colors ${
                  filter === val ? 'text-ink' : 'text-ink-30 hover:text-ink'
                }`}
              >
                {filterLabels[val]}
              </button>
            ))}
          </div>
        </section>

        {/* Top 3 podium editorial */}
        {!loading && sorted.length >= 3 && (
          <section className="border-t border-line">
            <div className="max-w-5xl mx-auto px-6 sm:px-10 py-16">
              <SectionNumber n={2} label="Top 3" />
              <div className="mt-10 grid grid-cols-1 sm:grid-cols-3 gap-12 sm:gap-8">
                {sorted.slice(0, 3).map((entry, i) => (
                  <ScrollReveal key={entry.student_id} delay={i * 0.1}>
                    <div className="text-center">
                      <p className="text-xs tracking-label text-ink-50 font-mono mb-4">
                        ({String(i + 1).padStart(2, '0')})
                      </p>
                      <p className={`font-display ${i === 0 ? 'text-7xl' : 'text-6xl'} text-ink leading-none`}>
                        {filter === 'exam_count' ? entry.exam_count : entry[filter].toFixed(1)}
                      </p>
                      {filter !== 'exam_count' && (
                        <p className="text-xs tracking-label text-ink-50 mt-3">Điểm</p>
                      )}
                      <p className="font-display italic text-2xl text-ink mt-6">
                        {entry.full_name}
                      </p>
                      {entry.class_name && (
                        <p className="text-xs tracking-label text-ink-50 mt-1">Lớp {entry.class_name}</p>
                      )}
                    </div>
                  </ScrollReveal>
                ))}
              </div>
            </div>
          </section>
        )}

        {/* Full table */}
        <section className="border-t border-line">
          <div className="max-w-5xl mx-auto px-6 sm:px-10 py-16">
            <SectionNumber n={3} label="Xếp hạng đầy đủ" />

            {loading ? (
              <div className="mt-12 space-y-3">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="border-t border-line py-5 animate-pulse">
                    <div className="grid grid-cols-12 gap-4">
                      <div className="col-span-1 h-3 bg-line w-8" />
                      <div className="col-span-7 h-4 bg-line w-2/3" />
                      <div className="col-span-1 h-3 bg-line" />
                      <div className="col-span-1 h-3 bg-line" />
                      <div className="col-span-1 h-3 bg-line" />
                    </div>
                  </div>
                ))}
              </div>
            ) : sorted.length === 0 ? (
              <p className="mt-12 font-display text-3xl text-ink-50 italic text-center py-16">
                Chưa có dữ liệu xếp hạng.
              </p>
            ) : (
              <div className="mt-12">
                <div className="grid grid-cols-12 gap-4 text-xs tracking-label text-ink-50 pb-4 border-b border-line">
                  <span className="col-span-1">#</span>
                  <span className="col-span-5 sm:col-span-6">Học sinh</span>
                  <span className="col-span-2 text-right">Điểm TB</span>
                  <span className="col-span-2 text-right">Cao nhất</span>
                  <span className="col-span-2 sm:col-span-1 text-right">Bài</span>
                </div>
                {sorted.map((entry, i) => {
                  const rank = i + 1
                  const isMe = entry.student_id === currentUserId
                  return (
                    <div
                      key={entry.student_id}
                      className={`grid grid-cols-12 gap-4 py-5 border-b border-line items-baseline ${
                        isMe ? 'bg-moss-bg -mx-6 sm:-mx-10 px-6 sm:px-10 border-l-2 border-moss' : ''
                      }`}
                    >
                      <span className="col-span-1 text-sm font-mono text-ink-50">
                        ({String(rank).padStart(2, '0')})
                      </span>
                      <div className="col-span-5 sm:col-span-6">
                        <p className={`font-display text-xl ${isMe ? 'text-moss italic' : 'text-ink'}`}>
                          {entry.full_name}{isMe && ' — bạn'}
                        </p>
                        {entry.class_name && (
                          <p className="text-xs tracking-label text-ink-50 mt-0.5">Lớp {entry.class_name}</p>
                        )}
                      </div>
                      <span className="col-span-2 text-right text-base text-ink tabular-nums">
                        {entry.avg_score.toFixed(2)}
                      </span>
                      <span className={`col-span-2 text-right text-base tabular-nums ${
                        entry.best_score >= 8 ? 'text-moss' : 'text-ink'
                      }`}>
                        {entry.best_score.toFixed(1)}
                      </span>
                      <span className="col-span-2 sm:col-span-1 text-right text-base text-ink-50 tabular-nums">
                        {entry.exam_count}
                      </span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </section>
      </main>

      <Footer />
    </div>
  )
}
