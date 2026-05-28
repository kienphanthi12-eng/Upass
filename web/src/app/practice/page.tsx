'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Header from '@/components/Header'
import Footer from '@/components/Footer'
import QuestionCard from '@/components/QuestionCard'
import SectionNumber from '@/components/ui/SectionNumber'
import DisplayHeading from '@/components/ui/DisplayHeading'
import { createClient } from '@/lib/supabase'
import type { Question, Topic, Level } from '@/lib/types'

const LEVELS: Level[] = ['Nhận biết', 'Thông hiểu', 'Vận dụng', 'Vận dụng cao']

function FilterChip({
  active, onClick, children,
}: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 text-sm tracking-label border transition-colors ${
        active
          ? 'border-ink bg-ink text-paper'
          : 'border-line text-ink-50 hover:border-ink hover:text-ink'
      }`}
    >
      {children}
    </button>
  )
}

export default function PracticePage() {
  const router = useRouter()
  const supabase = createClient()
  const [topics, setTopics] = useState<Topic[]>([])
  const [questions, setQuestions] = useState<Question[]>([])
  const [currentIdx, setCurrentIdx] = useState(0)
  const [selectedTopic, setSelectedTopic] = useState<number | null>(null)
  const [selectedLevel, setSelectedLevel] = useState<Level | null>(null)
  const [selectedType, setSelectedType] = useState<string>('')
  const [answers, setAnswers] = useState<Record<number, string>>({})
  const [revealed, setRevealed] = useState<Record<number, boolean>>({})
  const [loading, setLoading] = useState(false)
  const [started, setStarted] = useState(false)

  useEffect(() => {
    async function load() {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) { router.push('/login'); return }

      const { data } = await supabase.from('topics').select('id, subject_id, name, parent_id')
      if (data) setTopics(data as Topic[])
    }
    load()
  }, [router, supabase])

  useEffect(() => {
    if (typeof window !== 'undefined') {
      (window as unknown as Record<string, unknown>).__current_question__ = questions[currentIdx]
    }
    return () => {
      if (typeof window !== 'undefined') {
        delete (window as unknown as Record<string, unknown>).__current_question__
      }
    }
  }, [currentIdx, questions])

  const loadQuestions = async () => {
    setLoading(true)
    let query = supabase
      .from('questions')
      .select('id, exam_id, subject_id, topic_id, question_number, content, question_type, level, options, correct_answer, has_formula, has_image, topics(id, name)')
      .eq('is_hidden', false)
      .limit(30)

    if (selectedTopic) query = query.eq('topic_id', selectedTopic)
    if (selectedLevel) query = query.eq('level', selectedLevel)
    if (selectedType) query = query.eq('question_type', selectedType)
    query = query.not('correct_answer', 'is', null)

    const { data } = await query
    if (data) {
      const shuffled = [...data].sort(() => Math.random() - 0.5)
      setQuestions(shuffled as unknown as Question[])
      setCurrentIdx(0)
      setAnswers({})
      setRevealed({})
      setStarted(true)
    }
    setLoading(false)
  }

  const handleAnswer = useCallback((questionId: number, answer: string) => {
    setAnswers(prev => ({ ...prev, [questionId]: answer }))
    // Auto-reveal only for choice types — tự luận needs explicit submit
    const q = questions.find(x => x.id === questionId)
    if (q && q.question_type !== 'tu_luan') {
      setRevealed(prev => ({ ...prev, [questionId]: true }))
    }
  }, [questions])

  const handleSubmitFreeForm = () => {
    const q = questions[currentIdx]
    if (!q) return
    setRevealed(prev => ({ ...prev, [q.id]: true }))
  }

  const handleNext = () => {
    if (currentIdx < questions.length - 1) setCurrentIdx(i => i + 1)
  }

  const score = questions.length > 0
    ? questions.slice(0, currentIdx + 1).filter(q => answers[q.id] === q.correct_answer).length
    : 0

  if (!started) {
    return (
      <div className="flex flex-col min-h-screen">
        <Header />
        <main className="flex-1 max-w-3xl mx-auto w-full px-6 sm:px-10 py-16 sm:py-24">
          <SectionNumber n={1} label="Luyện tập" />
          <DisplayHeading size="lg" className="mt-6">
            Luyện theo <em className="italic">chủ đề</em>.
          </DisplayHeading>
          <p className="mt-6 text-base text-ink-70 leading-relaxed">
            Chọn bộ lọc và bắt đầu luyện tập với câu hỏi ngẫu nhiên. Có giải thích đáp án ngay sau mỗi câu.
          </p>

          <div className="mt-16 space-y-10">
            {/* Level */}
            <div>
              <p className="text-xs tracking-label text-ink-50 mb-4">Mức độ</p>
              <div className="flex flex-wrap gap-2">
                <FilterChip active={!selectedLevel} onClick={() => setSelectedLevel(null)}>
                  Tất cả
                </FilterChip>
                {LEVELS.map(lvl => (
                  <FilterChip
                    key={lvl}
                    active={selectedLevel === lvl}
                    onClick={() => setSelectedLevel(selectedLevel === lvl ? null : lvl)}
                  >
                    {lvl}
                  </FilterChip>
                ))}
              </div>
            </div>

            {/* Type */}
            <div>
              <p className="text-xs tracking-label text-ink-50 mb-4">Loại câu hỏi</p>
              <div className="flex flex-wrap gap-2">
                {[
                  { val: '', label: 'Tất cả' },
                  { val: 'trac_nghiem', label: 'Trắc nghiệm' },
                  { val: 'dung_sai', label: 'Đúng/Sai' },
                  { val: 'tu_luan', label: 'Tự luận' },
                ].map(({ val, label }) => (
                  <FilterChip
                    key={val}
                    active={selectedType === val}
                    onClick={() => setSelectedType(val)}
                  >
                    {label}
                  </FilterChip>
                ))}
              </div>
            </div>

            {/* Topic */}
            <div>
              <p className="text-xs tracking-label text-ink-50 mb-4">Chủ đề</p>
              <select
                value={selectedTopic ?? ''}
                onChange={e => setSelectedTopic(e.target.value ? Number(e.target.value) : null)}
                className="w-full bg-transparent border-0 border-b border-line py-3 text-base text-ink focus:outline-none focus:border-ink"
              >
                <option value="">Tất cả chủ đề</option>
                {topics.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
              </select>
            </div>

            <button
              onClick={loadQuestions}
              disabled={loading}
              className="mt-4 inline-flex items-center gap-2 px-8 py-4 bg-ink text-paper text-sm tracking-label hover:bg-moss transition-colors disabled:opacity-50"
            >
              {loading
                ? <span className="w-4 h-4 border border-paper/30 border-t-paper rounded-full animate-spin" />
                : null}
              {loading ? 'Đang tải câu hỏi…' : 'Bắt đầu luyện tập →'}
            </button>
          </div>
        </main>
        <Footer />
      </div>
    )
  }

  const currentQuestion = questions[currentIdx]
  const isAnswered = revealed[currentQuestion?.id]

  return (
    <div className="flex flex-col min-h-screen">
      <Header />
      <main className="flex-1 max-w-3xl mx-auto w-full px-6 sm:px-10 py-10">
        {/* Progress */}
        <div className="flex items-center justify-between text-xs tracking-label mb-4">
          <span className="text-ink-50">
            Câu <span className="text-ink font-mono">({String(currentIdx + 1).padStart(2, '0')})</span> / ({String(questions.length).padStart(2, '0')})
          </span>
          <div className="flex items-center gap-6">
            <span className="text-moss">{score} đúng</span>
            <button
              onClick={() => setStarted(false)}
              className="text-ink-50 hover:text-ink link-editorial"
            >
              ← Chọn lại
            </button>
          </div>
        </div>

        <div className="h-px bg-line mb-12 relative">
          <div
            className="absolute top-0 left-0 h-px bg-ink transition-all"
            style={{ width: `${((currentIdx + 1) / questions.length) * 100}%` }}
          />
        </div>

        {currentQuestion && (
          <>
            <QuestionCard
              question={currentQuestion}
              index={currentIdx}
              selectedAnswer={answers[currentQuestion.id]}
              onAnswer={handleAnswer}
              showResult={isAnswered}
            />

            {/* Tự luận: explicit submit button — typing alone doesn't reveal */}
            {currentQuestion.question_type === 'tu_luan' && !isAnswered && (
              <button
                onClick={handleSubmitFreeForm}
                disabled={!answers[currentQuestion.id]?.trim()}
                className="mt-10 inline-flex items-center gap-2 px-7 py-3.5 bg-ink text-paper text-sm tracking-label hover:bg-moss transition-colors disabled:opacity-40"
              >
                Trả lời →
              </button>
            )}

            {isAnswered && (
              <button
                onClick={handleNext}
                disabled={currentIdx === questions.length - 1}
                className="mt-10 inline-flex items-center gap-2 px-7 py-3.5 bg-ink text-paper text-sm tracking-label hover:bg-moss transition-colors disabled:opacity-40"
              >
                {currentIdx === questions.length - 1 ? 'Hoàn thành →' : 'Câu tiếp theo →'}
              </button>
            )}
          </>
        )}

        {currentIdx === questions.length - 1 && isAnswered && (
          <div className="mt-12 border-t border-line pt-10 text-center">
            <p className="font-display text-4xl text-ink italic mb-2">Hoàn thành.</p>
            <p className="text-base text-ink-70">
              Đúng <em className="italic text-ink">{score}/{questions.length}</em> câu.
            </p>
            <button
              onClick={loadQuestions}
              className="mt-8 inline-flex items-center gap-2 px-7 py-3.5 bg-ink text-paper text-sm tracking-label hover:bg-moss transition-colors"
            >
              Luyện tiếp →
            </button>
          </div>
        )}
      </main>
      <Footer />
    </div>
  )
}
