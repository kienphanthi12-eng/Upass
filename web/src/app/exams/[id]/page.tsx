'use client'

import { useState, useEffect, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Header from '@/components/Header'
import QuestionCard, { renderContent, getDisplayContent, LEVEL_COLORS } from '@/components/QuestionCard'
import ReportButton from '@/components/ReportButton'
import Timer from '@/components/Timer'
import SectionNumber from '@/components/ui/SectionNumber'
import DisplayHeading from '@/components/ui/DisplayHeading'
import { createClient } from '@/lib/supabase'
import type { Exam, Question, AnswerMap } from '@/lib/types'
import { examDisplayName } from '@/lib/types'
import { AlertTriangle } from 'lucide-react'
import { notify } from '@/lib/notify'

const EXAM_DURATION = 90 * 60

export default function TakeExamPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const supabase = createClient()

  const [exam, setExam] = useState<Exam | null>(null)
  const [questions, setQuestions] = useState<Question[]>([])
  const [answers, setAnswers] = useState<AnswerMap>({})
  const [currentIdx, setCurrentIdx] = useState(0)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [confirmSubmit, setConfirmSubmit] = useState(false)
  const [started, setStarted] = useState(false)
  const [startTime, setStartTime] = useState<number>(0)
  const [showMobilePalette, setShowMobilePalette] = useState(false)
  const [submissionId, setSubmissionId] = useState<string | null>(null)

  const scrollToQuestion = (idx: number) => {
    const element = document.getElementById(`q-card-${idx}`)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }

  const handleStartExam = async () => {
    setStarted(true)
    setStartTime(Date.now())
    try {
      const { data: { user } } = await supabase.auth.getUser()
      if (user) {
        // Get student name
        const { data: student } = await supabase
          .from('students')
          .select('full_name')
          .eq('id', user.id)
          .single()

        // Send exam start notification
        if (student) {
          await notify({
            type: 'exam_start',
            studentName: student.full_name,
            examTitle: exam ? examDisplayName(exam) : `Đề #${id}`,
          })
        }

        // Check for existing in-progress attempt for this exam
        const { data: existing } = await supabase
          .from('exam_submissions')
          .select('id')
          .eq('student_id', user.id)
          .eq('exam_id', Number(id))
          .eq('status', 'in_progress')
          .limit(1)
          .maybeSingle()

        if (existing) {
          setSubmissionId(existing.id)
        } else {
          const { data: submission } = await supabase
            .from('exam_submissions')
            .insert({
              student_id: user.id,
              exam_id: Number(id),
              status: 'in_progress',
              total_questions: questions.length,
              correct_count: 0,
            })
            .select('id')
            .single()

          if (submission) {
            setSubmissionId(submission.id)
          }
        }
      }
    } catch (e) {
      console.error('Error starting in-progress submission:', e)
    }
  }

  useEffect(() => {
    async function load() {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) { router.push('/login'); return }

      const [examRes, questRes] = await Promise.all([
        supabase
          .from('exams')
          .select('id, title, display_title, year, exam_type, subject_id, subjects(id, name, code)')
          .eq('id', id)
          .single(),
        supabase
          .from('questions')
          .select('id, exam_id, subject_id, topic_id, question_number, content, question_type, level, options, correct_answer, has_formula, has_image, topics(id, name), subjects(id, name, code)')
          .eq('exam_id', id)
          .eq('is_hidden', false)
          .order('question_number'),
      ])
      if (examRes.data) setExam(examRes.data as unknown as Exam)
      if (questRes.data) setQuestions(questRes.data as unknown as Question[])
      setLoading(false)
    }
    load()
  }, [id, router, supabase])

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

  const handleAnswer = useCallback((questionId: number, answer: string) => {
    setAnswers(prev => ({ ...prev, [questionId]: answer }))
  }, [])

  const handleSubmit = async () => {
    setSubmitting(true)
    const { data: { user } } = await supabase.auth.getUser()

    const timeTaken = Math.floor((Date.now() - startTime) / 1000)
    let correctCount = 0
    const answerRows: { submission_id: string; question_id: number; answer: string | null; is_correct: boolean }[] = []

    questions.forEach(q => {
      const userAnswer = answers[q.id] ?? null
      const isCorrect = !!q.correct_answer && userAnswer === q.correct_answer
      if (isCorrect) correctCount++
      answerRows.push({
        submission_id: '',
        question_id: q.id,
        answer: userAnswer,
        is_correct: isCorrect,
      })
    })

    const score = questions.length > 0 ? (correctCount / questions.length) * 10 : 0

    if (user) {
      // Get student name for notification
      const { data: student } = await supabase
        .from('students')
        .select('full_name')
        .eq('id', user.id)
        .single()

      let submission = null
      if (submissionId) {
        const { data } = await supabase
          .from('exam_submissions')
          .update({
            time_taken: timeTaken,
            score: Math.round(score * 100) / 100,
            total_questions: questions.length,
            correct_count: correctCount,
            status: 'completed',
            submitted_at: new Date().toISOString(),
          })
          .eq('id', submissionId)
          .select('id')
          .single()
        submission = data
      } else {
        const { data } = await supabase
          .from('exam_submissions')
          .insert({
            student_id: user.id,
            exam_id: Number(id),
            time_taken: timeTaken,
            score: Math.round(score * 100) / 100,
            total_questions: questions.length,
            correct_count: correctCount,
            status: 'completed',
          })
          .select('id')
          .single()
        submission = data
      }

      if (submission) {
        await supabase.from('student_answers').insert(
          answerRows.map(r => ({ ...r, submission_id: submission.id }))
        )

        // Send exam submit notification
        if (student && exam) {
          await notify({
            type: 'exam_submit',
            studentName: student.full_name,
            examTitle: examDisplayName(exam),
            score: Math.round(score * 100) / 100,
            correct: correctCount,
            total: questions.length,
          })
        }

        router.push(`/exams/${id}/result?sub=${submission.id}`)
        return
      }
    }

    sessionStorage.setItem(`exam_result_${id}`, JSON.stringify({
      answers, correctCount, totalQuestions: questions.length,
      score: Math.round(score * 100) / 100, timeTaken,
    }))
    router.push(`/exams/${id}/result`)
  }

  const answeredCount = Object.keys(answers).length
  const unansweredCount = questions.length - answeredCount

  if (loading) {
    return (
      <div className="flex flex-col min-h-screen">
        <Header />
        <div className="flex-1 flex items-center justify-center">
          <p className="font-display text-3xl text-ink-50 italic">Đang tải đề thi…</p>
        </div>
      </div>
    )
  }

  if (!exam || questions.length === 0) {
    return (
      <div className="flex flex-col min-h-screen">
        <Header />
        <div className="flex-1 flex items-center justify-center px-6">
          <div className="text-center max-w-md">
            <AlertTriangle size={36} className="text-ink-30 mx-auto mb-4" />
            <p className="font-display text-3xl text-ink italic">Không tìm thấy đề thi.</p>
            <p className="text-sm text-ink-50 mt-2">Hoặc đề chưa có câu hỏi nào.</p>
          </div>
        </div>
      </div>
    )
  }

  // Start screen — editorial intro
  if (!started) {
    return (
      <div className="flex flex-col min-h-screen">
        <Header />
        <main className="flex-1 flex items-center">
          <div className="max-w-3xl mx-auto px-6 sm:px-10 py-16 sm:py-24 w-full">
            <SectionNumber n={1} label="Trước khi bắt đầu" />
            <DisplayHeading size="lg" className="mt-6 max-w-2xl">
              <em className="italic">{examDisplayName(exam)}</em>.
            </DisplayHeading>
            <p className="mt-4 text-sm tracking-label text-ink-50">{exam.year}</p>

            {/* Stats inline */}
            <div className="mt-12 grid grid-cols-3 gap-8 border-y border-line py-10">
              {[
                { v: questions.length, l: 'câu hỏi' },
                { v: 90, l: 'phút' },
                { v: 10, l: 'điểm tối đa' },
              ].map(s => (
                <div key={s.l}>
                  <p className="font-display text-5xl sm:text-6xl text-ink leading-none">{s.v}</p>
                  <p className="mt-2 text-xs tracking-label text-ink-50">{s.l}</p>
                </div>
              ))}
            </div>

            {/* Note */}
            <div className="mt-10 border-l-2 border-moss pl-6">
              <p className="text-xs tracking-label text-moss mb-3">Lưu ý</p>
              <ul className="space-y-2 text-base text-ink-70">
                <li>— Đồng hồ đếm ngược 90 phút sẽ bắt đầu khi bạn bấm &quot;Bắt đầu&quot;</li>
                <li>— Bài sẽ tự động nộp khi hết giờ</li>
                <li>— Không thoát trình duyệt trong khi làm bài</li>
              </ul>
            </div>

            <div className="mt-12 flex items-center gap-6">
              <button
                onClick={handleStartExam}
                className="inline-flex items-center gap-3 px-8 py-4 bg-ink text-paper text-sm tracking-label hover:bg-moss transition-colors"
              >
                Bắt đầu làm bài <span aria-hidden>→</span>
              </button>
              <button
                onClick={() => router.back()}
                className="text-sm tracking-label text-ink-50 link-editorial"
              >
                Quay lại
              </button>
            </div>
          </div>
        </main>
      </div>
    )
  }

  const currentQuestion = questions[currentIdx]

  return (
    <div className="flex flex-col min-h-screen">
      {/* Exam toolbar — editorial top bar */}
      <div className="sticky top-0 z-40 bg-paper/95 backdrop-blur-md border-b border-line">
        <div className="max-w-7xl mx-auto px-6 sm:px-10 py-4 flex items-center justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <p className="text-xs tracking-label text-ink-50">
                Đã trả lời {answeredCount} / {questions.length}
              </p>
              <button
                onClick={() => setShowMobilePalette(true)}
                className="lg:hidden text-[10px] tracking-wider uppercase font-semibold border border-line hover:border-ink hover:text-ink px-2.5 py-1 rounded transition-colors"
              >
                Phiếu trả lời
              </button>
            </div>
            <p className="font-display text-lg sm:text-xl text-ink truncate mt-0.5">
              {examDisplayName(exam)}
            </p>
          </div>

          <div className="flex items-center gap-6 shrink-0">
            <Timer initialSeconds={EXAM_DURATION} onTimeUp={handleSubmit} />
            <button
              onClick={() => setConfirmSubmit(true)}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-ink text-paper text-sm tracking-label hover:bg-moss transition-colors"
            >
              Nộp bài <span aria-hidden>→</span>
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 max-w-7xl mx-auto w-full px-6 sm:px-10 py-10 grid grid-cols-12 gap-10 items-start">
        {/* Left Column: Continuous Exam Booklet */}
        <div className="col-span-12 lg:col-span-8 min-w-0">
          <div className="bg-white border border-line rounded-2xl p-6 sm:p-10 shadow-sm space-y-8 font-serif">
            {/* Booklet Header (Cover Style) */}
            <div className="border-b-2 border-double border-ink/30 pb-8 mb-6 font-sans">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 text-xs text-ink-50 font-semibold tracking-wider uppercase mb-6">
                <div>BỘ GIÁO DỤC VÀ ĐÀO TẠO</div>
                <div className="sm:text-right">KỲ THI TỐT NGHIỆP TRUNG HỌC PHỔ THÔNG</div>
              </div>
              <div className="text-center max-w-xl mx-auto my-4">
                <span className="text-xs tracking-widest text-moss font-bold uppercase block mb-1">ĐỀ THI CHÍNH THỨC</span>
                <h2 className="font-display text-3xl sm:text-4xl text-ink font-extrabold tracking-tight uppercase leading-none">
                  Môn {exam.subjects?.name || 'Học'}
                </h2>
                <p className="text-xs text-ink-50 mt-2 font-medium tracking-wide">
                  {examDisplayName(exam)}
                </p>
              </div>
              <div className="mt-8 grid grid-cols-3 gap-4 border-t border-line-soft pt-6 text-center text-xs text-ink-70 font-semibold tracking-wide">
                <div>
                  <span className="text-ink-30 block text-[10px] uppercase font-bold mb-1">Mã đề thi</span>
                  <span className="font-mono text-sm font-bold text-ink">101</span>
                </div>
                <div>
                  <span className="text-ink-30 block text-[10px] uppercase font-bold mb-1">Số câu hỏi</span>
                  <span className="text-sm font-bold text-ink">{questions.length} câu</span>
                </div>
                <div>
                  <span className="text-ink-30 block text-[10px] uppercase font-bold mb-1">Thời gian làm bài</span>
                  <span className="text-sm font-bold text-ink">90 phút</span>
                </div>
              </div>
            </div>

            {/* Booklet Content (Continuous Questions) */}
            <div className="space-y-0">
              {questions.map((q, i) => {
                const selected = answers[q.id]
                const optKeys = q.options ? Object.keys(q.options).sort() : ['A', 'B', 'C', 'D']
                const isCurrent = currentIdx === i
                const showTopicHeader = i === 0 || questions[i - 1].topic_id !== q.topic_id

                return (
                  <div key={q.id} className="space-y-0">
                    {showTopicHeader && q.topics?.name && (
                      <div className="pt-8 pb-3 border-b border-dashed border-line mb-6 font-sans scroll-mt-24">
                        <span className="text-[10px] tracking-wider uppercase font-bold text-moss">Chuyên đề</span>
                        <h3 className="font-display text-lg text-ink font-bold italic mt-0.5">{q.topics.name}</h3>
                      </div>
                    )}

                    <div
                      id={`q-card-${i}`}
                      onClick={() => setCurrentIdx(i)}
                      className={`group/question py-6 border-b border-line-soft last:border-b-0 scroll-mt-24 transition-all duration-300 -mx-4 px-4 rounded-xl cursor-pointer ${
                        isCurrent 
                          ? 'bg-moss-bg/15 border-l-4 border-l-moss pl-3' 
                          : 'hover:bg-paper-soft/10 border-l-4 border-l-transparent'
                      }`}
                    >
                      {/* Question Header & Level / Report Button */}
                      <div className="flex items-center justify-between gap-3 mb-3">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-sans text-xs font-bold text-ink">
                            Câu {i + 1}.
                          </span>
                          {q.level && (
                            <span className={`font-sans text-[9px] tracking-wider uppercase font-bold px-2 py-0.5 rounded-full ${
                              q.level === 'Nhận biết' ? 'bg-emerald-50 text-emerald-700 border border-emerald-100' :
                              q.level === 'Thông hiểu' ? 'bg-blue-50 text-blue-700 border border-blue-100' :
                              q.level === 'Vận dụng' ? 'bg-orange-50 text-orange-700 border border-orange-100' :
                              'bg-red-50 text-red-700 border border-red-100'
                            }`}>
                              {q.level}
                            </span>
                          )}
                        </div>
                        <div className="opacity-0 group-hover/question:opacity-100 transition-opacity">
                          <ReportButton questionId={q.id} />
                        </div>
                      </div>

                      {/* Question Content */}
                      <div className="text-gray-800 text-[15px] leading-relaxed mb-4 font-serif font-medium">
                        {renderContent(getDisplayContent(q))}
                      </div>

                      {/* Render Choices based on Type */}
                      {q.question_type === 'trac_nghiem' && !q.options && (
                        <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-700 font-sans">
                          ⚠️ Câu hỏi này chưa có đáp án cấu trúc. Xem nội dung câu hỏi bên trên.
                        </div>
                      )}

                      {q.question_type === 'trac_nghiem' && q.options && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-2 mt-2 pl-1">
                          {optKeys.map(key => {
                            const optText = q.options?.[key]
                            if (!optText) return null
                            const isSelected = selected === key
                            return (
                              <div
                                key={key}
                                onClick={(e) => {
                                  e.stopPropagation()
                                  handleAnswer(q.id, key)
                                }}
                                className="flex items-start gap-2.5 py-1.5 px-2 rounded-lg cursor-pointer hover:bg-paper-soft/40 transition-colors select-none text-sm group/option"
                              >
                                <span className={`inline-flex items-center justify-center w-5 h-5 rounded-full text-[11px] font-sans font-bold shrink-0 transition-all ${
                                  isSelected
                                    ? 'bg-moss text-paper border border-moss scale-105 shadow-sm'
                                    : 'border border-line text-ink-40 group-hover/option:border-ink group-hover/option:text-ink'
                                }`}>
                                  {key}
                                </span>
                                <span className={`font-sans text-[13px] leading-relaxed pt-0.5 ${isSelected ? 'text-ink font-semibold' : 'text-ink-70'}`}>
                                  {renderContent(optText)}
                                </span>
                              </div>
                            )
                          })}
                        </div>
                      )}

                      {q.question_type === 'dung_sai' && q.options && (
                        <div className="space-y-2 mt-3 pl-1">
                          {optKeys.map((key, idx) => {
                            const subText = q.options?.[key]
                            if (!subText) return null
                            const myChar = (selected && idx < selected.length)
                              ? selected[idx].toUpperCase() : undefined
                            return (
                              <div key={key} className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-2 bg-paper-soft/10 rounded-lg border border-line-soft/80 font-sans text-xs">
                                <div className="flex items-start gap-2">
                                  <span className="shrink-0 w-5 h-5 rounded-full bg-paper-deep text-ink font-bold flex items-center justify-center text-[10px]">{key}</span>
                                  <div className="leading-relaxed text-ink-70 pt-0.5">{renderContent(subText)}</div>
                                </div>
                                <div className="flex items-center gap-1.5 pl-7 sm:pl-0 shrink-0" onClick={e => e.stopPropagation()}>
                                  {(['D', 'S'] as const).map(val => {
                                    const isSel = myChar === val
                                    return (
                                      <button
                                        key={val}
                                        onClick={() => {
                                          const base = (selected || '').padEnd(4, '?').split('')
                                          base[idx] = val
                                          handleAnswer(q.id, base.join(''))
                                        }}
                                        className={`px-2 py-0.5 rounded border text-[10px] font-semibold transition-all ${
                                          isSel
                                            ? 'bg-moss text-paper border-moss font-bold shadow-sm'
                                            : 'border-line text-ink-40 hover:border-ink hover:text-ink bg-white'
                                        }`}
                                      >
                                        {val === 'D' ? 'Đúng' : 'Sai'}
                                      </button>
                                    )
                                  })}
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      )}

                      {q.question_type === 'dung_sai' && !q.options && (
                        <div className="flex gap-3 mt-3 pl-1 font-sans text-xs">
                          {['D', 'S'].map(val => {
                            const isSel = selected === val
                            return (
                              <button
                                key={val}
                                onClick={(e) => {
                                  e.stopPropagation()
                                  handleAnswer(q.id, val)
                                }}
                                className={`flex-1 py-1.5 rounded-lg border font-semibold transition-all ${
                                  isSel
                                    ? 'bg-moss text-paper border-moss font-bold'
                                    : 'border-line text-ink-70 hover:border-ink hover:bg-paper-soft/10 bg-white'
                                }`}
                              >
                                {val === 'D' ? 'Đúng' : 'Sai'}
                              </button>
                            )
                          })}
                        </div>
                      )}

                      {q.question_type === 'tu_luan' && (
                        <div className="mt-3 pl-1 font-sans">
                          <textarea
                            value={selected || ''}
                            onClick={e => e.stopPropagation()}
                            onChange={e => handleAnswer(q.id, e.target.value)}
                            placeholder="Nhập câu trả lời của bạn..."
                            rows={3}
                            className="w-full px-3 py-2 border border-line rounded-lg text-xs text-ink bg-paper-soft/10 focus:outline-none focus:border-ink resize-none focus:bg-white transition-all"
                          />
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>

        {/* Right Column: Sticky OMR Bubble Sheet */}
        <aside className="col-span-12 lg:col-span-4 sticky top-28 bg-white/95 backdrop-blur-sm border border-line rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between pb-3 border-b border-line mb-4">
            <span className="font-display text-xl text-ink font-semibold">Phiếu trả lời</span>
            <span className="text-xs text-ink-50 font-mono">
              Đã làm: <strong className="text-moss">{answeredCount}</strong> / {questions.length} câu
            </span>
          </div>

          {/* Progress bar */}
          <div className="w-full h-1 bg-line-soft rounded-full overflow-hidden mb-5">
            <div
              className="h-full bg-moss rounded-full transition-all duration-300"
              style={{ width: `${questions.length > 0 ? (answeredCount / questions.length) * 100 : 0}%` }}
            />
          </div>

          <div className="flex gap-6 max-h-[calc(100vh-250px)] overflow-y-auto pr-1.5 font-mono scrollbar-thin">
            {/* Column 1 (Questions 1 to Half) */}
            <div className="flex-1 flex flex-col gap-2 border-r border-line-soft pr-3">
              {questions.slice(0, Math.ceil(questions.length / 2)).map((q, i) => {
                const idx = i
                const selected = answers[q.id]
                const optKeys = q.options ? Object.keys(q.options).sort() : ['A', 'B', 'C', 'D']
                const subKeys = q.options ? Object.keys(q.options).sort() : ['A', 'B', 'C', 'D']
                const isCurrent = currentIdx === idx
                return (
                  <div
                    key={q.id}
                    onClick={() => {
                      setCurrentIdx(idx)
                      scrollToQuestion(idx)
                    }}
                    className={`flex flex-col py-1.5 px-2 rounded-md transition-colors group cursor-pointer ${
                      selected ? 'bg-moss-bg/20' : 'hover:bg-paper-soft/40'
                    } ${isCurrent ? 'ring-1 ring-moss-soft bg-moss-bg/10 border-l-2 border-l-moss' : 'border-l-2 border-l-transparent'}`}
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className={`text-xs font-semibold transition-colors ${
                        selected ? 'text-moss' : 'text-ink-50 group-hover:text-ink'
                      }`}>
                        {String(idx + 1).padStart(2, '0')}.
                      </span>
                      
                      {/* trac_nghiem standard bubbles */}
                      {q.question_type === 'trac_nghiem' && (
                        <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
                          {optKeys.map(opt => {
                            const isSelected = selected === opt
                            return (
                              <button
                                key={opt}
                                onClick={() => handleAnswer(q.id, opt)}
                                className={`w-6 h-6 rounded-full text-[10px] font-bold flex items-center justify-center border transition-all duration-200 ${
                                  isSelected
                                    ? 'bg-ink text-paper border-ink scale-110 shadow-sm'
                                    : 'border-line text-ink-30 bg-white hover:border-ink hover:text-ink'
                                }`}
                              >
                                {opt}
                              </button>
                            )
                          })}
                        </div>
                      )}

                      {/* dung_sai without options */}
                      {q.question_type === 'dung_sai' && !q.options && (
                        <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
                          {(['D', 'S'] as const).map(val => {
                            const isSel = selected === val
                            return (
                              <button
                                key={val}
                                onClick={() => handleAnswer(q.id, val)}
                                className={`w-7 h-5 rounded text-[9px] font-bold flex items-center justify-center border transition-all ${
                                  isSel
                                    ? 'bg-moss text-paper border-moss font-bold shadow-sm'
                                    : 'border-line text-ink-30 bg-white hover:border-ink hover:text-ink'
                                }`}
                              >
                                {val === 'D' ? 'Đ' : 'S'}
                              </button>
                            )
                          })}
                        </div>
                      )}
                    </div>

                    {/* dung_sai with options nested */}
                    {q.question_type === 'dung_sai' && q.options && (
                      <div className="flex flex-col gap-1 w-full mt-1 bg-paper-soft/40 p-1.5 rounded border border-line-soft" onClick={e => e.stopPropagation()}>
                        {subKeys.map((subKey, subIdx) => {
                          const myChar = (selected && subIdx < selected.length) ? selected[subIdx].toUpperCase() : '?'
                          return (
                            <div key={subKey} className="flex items-center justify-between text-[10px] gap-1">
                              <span className="text-ink-50 font-bold font-sans">{subKey.toLowerCase()}:</span>
                              <div className="flex items-center gap-0.5">
                                {(['D', 'S'] as const).map(val => {
                                  const isSel = myChar === val
                                  return (
                                    <button
                                      key={val}
                                      onClick={() => {
                                        const base = (selected || '').padEnd(4, '?').split('')
                                        base[subIdx] = val
                                        handleAnswer(q.id, base.join(''))
                                      }}
                                      className={`w-5 h-4 rounded text-[8px] font-bold flex items-center justify-center border transition-all ${
                                        isSel
                                          ? 'bg-moss text-paper border-moss'
                                          : 'border-line text-ink-30 bg-white hover:border-ink hover:text-ink'
                                      }`}
                                    >
                                      {val === 'D' ? 'Đ' : 'S'}
                                    </button>
                                  )
                                })}
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    )}

                    {/* tu_luan text box */}
                    {q.question_type === 'tu_luan' && (
                      <div className="w-full mt-1" onClick={e => e.stopPropagation()}>
                        <input
                          type="text"
                          value={selected || ''}
                          onChange={e => handleAnswer(q.id, e.target.value)}
                          placeholder="Đáp án..."
                          className="w-full px-2 py-1 border border-line rounded text-[11px] text-ink focus:outline-none focus:border-ink font-sans bg-white"
                        />
                      </div>
                    )}
                  </div>
                )
              })}
            </div>

            {/* Column 2 (Questions Half+1 to Total) */}
            <div className="flex-1 flex flex-col gap-2">
              {questions.slice(Math.ceil(questions.length / 2)).map((q, i) => {
                const idx = Math.ceil(questions.length / 2) + i
                const selected = answers[q.id]
                const optKeys = q.options ? Object.keys(q.options).sort() : ['A', 'B', 'C', 'D']
                const subKeys = q.options ? Object.keys(q.options).sort() : ['A', 'B', 'C', 'D']
                const isCurrent = currentIdx === idx
                return (
                  <div
                    key={q.id}
                    onClick={() => {
                      setCurrentIdx(idx)
                      scrollToQuestion(idx)
                    }}
                    className={`flex flex-col py-1.5 px-2 rounded-md transition-colors group cursor-pointer ${
                      selected ? 'bg-moss-bg/20' : 'hover:bg-paper-soft/40'
                    } ${isCurrent ? 'ring-1 ring-moss-soft bg-moss-bg/10 border-l-2 border-l-moss' : 'border-l-2 border-l-transparent'}`}
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className={`text-xs font-semibold transition-colors ${
                        selected ? 'text-moss' : 'text-ink-50 group-hover:text-ink'
                      }`}>
                        {String(idx + 1).padStart(2, '0')}.
                      </span>
                      
                      {/* trac_nghiem standard bubbles */}
                      {q.question_type === 'trac_nghiem' && (
                        <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
                          {optKeys.map(opt => {
                            const isSelected = selected === opt
                            return (
                              <button
                                key={opt}
                                onClick={() => handleAnswer(q.id, opt)}
                                className={`w-6 h-6 rounded-full text-[10px] font-bold flex items-center justify-center border transition-all duration-200 ${
                                  isSelected
                                    ? 'bg-ink text-paper border-ink scale-110 shadow-sm'
                                    : 'border-line text-ink-30 bg-white hover:border-ink hover:text-ink'
                                }`}
                              >
                                {opt}
                              </button>
                            )
                          })}
                        </div>
                      )}

                      {/* dung_sai without options */}
                      {q.question_type === 'dung_sai' && !q.options && (
                        <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
                          {(['D', 'S'] as const).map(val => {
                            const isSel = selected === val
                            return (
                              <button
                                key={val}
                                onClick={() => handleAnswer(q.id, val)}
                                className={`w-7 h-5 rounded text-[9px] font-bold flex items-center justify-center border transition-all ${
                                  isSel
                                    ? 'bg-moss text-paper border-moss font-bold shadow-sm'
                                    : 'border-line text-ink-30 bg-white hover:border-ink hover:text-ink'
                                }`}
                              >
                                {val === 'D' ? 'Đ' : 'S'}
                              </button>
                            )
                          })}
                        </div>
                      )}
                    </div>

                    {/* dung_sai with options nested */}
                    {q.question_type === 'dung_sai' && q.options && (
                      <div className="flex flex-col gap-1 w-full mt-1 bg-paper-soft/40 p-1.5 rounded border border-line-soft" onClick={e => e.stopPropagation()}>
                        {subKeys.map((subKey, subIdx) => {
                          const myChar = (selected && subIdx < selected.length) ? selected[subIdx].toUpperCase() : '?'
                          return (
                            <div key={subKey} className="flex items-center justify-between text-[10px] gap-1">
                              <span className="text-ink-50 font-bold font-sans">{subKey.toLowerCase()}:</span>
                              <div className="flex items-center gap-0.5">
                                {(['D', 'S'] as const).map(val => {
                                  const isSel = myChar === val
                                  return (
                                    <button
                                      key={val}
                                      onClick={() => {
                                        const base = (selected || '').padEnd(4, '?').split('')
                                        base[subIdx] = val
                                        handleAnswer(q.id, base.join(''))
                                      }}
                                      className={`w-5 h-4 rounded text-[8px] font-bold flex items-center justify-center border transition-all ${
                                        isSel
                                          ? 'bg-moss text-paper border-moss'
                                          : 'border-line text-ink-30 bg-white hover:border-ink hover:text-ink'
                                      }`}
                                    >
                                      {val === 'D' ? 'Đ' : 'S'}
                                    </button>
                                  )
                                })}
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    )}

                    {/* tu_luan text box */}
                    {q.question_type === 'tu_luan' && (
                      <div className="w-full mt-1" onClick={e => e.stopPropagation()}>
                        <input
                          type="text"
                          value={selected || ''}
                          onChange={e => handleAnswer(q.id, e.target.value)}
                          placeholder="Đáp án..."
                          className="w-full px-2 py-1 border border-line rounded text-[11px] text-ink focus:outline-none focus:border-ink font-sans bg-white"
                        />
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        </aside>
      </div>

      {/* Confirm submit modal */}
      {confirmSubmit && (
        <div className="fixed inset-0 bg-ink/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-paper border border-line p-8 max-w-md w-full">
            <p className="text-xs tracking-label text-ink-50 mb-3">Xác nhận</p>
            <p className="font-display text-3xl text-ink mb-6">
              <em className="italic">Nộp bài</em>?
            </p>
            {unansweredCount > 0 && (
              <div className="border-l-2 border-sun pl-4 py-2 mb-6">
                <p className="text-sm text-ink-70">
                  Còn <strong className="text-ink">{unansweredCount}</strong> câu chưa trả lời.
                </p>
              </div>
            )}
            <p className="text-sm text-ink-50 mb-8">
              Bài đã nộp không thể sửa lại.
            </p>
            <div className="flex items-center gap-6">
              <button
                onClick={() => setConfirmSubmit(false)}
                className="text-sm tracking-label text-ink-50 link-editorial"
              >
                Làm tiếp
              </button>
              <button
                onClick={() => { setConfirmSubmit(false); handleSubmit() }}
                disabled={submitting}
                className="ml-auto inline-flex items-center gap-2 px-6 py-3 bg-ink text-paper text-sm tracking-label hover:bg-moss disabled:opacity-50"
              >
                {submitting ? 'Đang nộp…' : 'Nộp bài ngay →'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Mobile/Tablet Drawer */}
      {showMobilePalette && (
        <div className="fixed inset-0 bg-ink/40 backdrop-blur-sm z-50 lg:hidden flex items-end justify-center" onClick={() => setShowMobilePalette(false)}>
          <div className="bg-paper w-full max-h-[80vh] overflow-y-auto border-t border-line p-6 flex flex-col animate-in slide-in-from-bottom duration-200" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6 pb-2 border-b border-line">
              <p className="text-xs tracking-label text-ink-50">Danh sách câu hỏi</p>
              <button onClick={() => setShowMobilePalette(false)} className="text-xs tracking-label text-ink hover:text-moss font-semibold">
                Đóng
              </button>
            </div>
            <div className="grid grid-cols-6 sm:grid-cols-8 gap-2 mb-6">
              {questions.map((q, i) => {
                const answered = answers[q.id] !== undefined
                const current = i === currentIdx
                return (
                  <button
                    key={q.id}
                    onClick={() => {
                      setCurrentIdx(i)
                      scrollToQuestion(i)
                      setShowMobilePalette(false)
                    }}
                    className={`aspect-square flex items-center justify-center text-xs font-mono transition-colors ${
                      current
                        ? 'bg-ink text-paper font-semibold'
                        : answered
                        ? 'bg-moss-bg text-moss border border-moss/30'
                        : 'border border-line text-ink-50 hover:border-ink hover:text-ink'
                    }`}
                  >
                    {i + 1}
                  </button>
                )
              })}
            </div>
            <div className="space-y-2 text-xs text-ink-50 border-t border-line pt-4">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 bg-moss-bg border border-moss/30" />
                Đã trả lời ({answeredCount})
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 border border-line" />
                Chưa trả lời ({unansweredCount})
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 bg-ink" />
                Câu hiện tại
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
