'use client'

import { useState, useEffect, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Save, Eye, Trash2, Plus, CheckCircle, AlertCircle, Send, Printer } from 'lucide-react'
import LatexEditor, { RenderLatex } from '@/components/teacher/LatexEditor'
import type { DraftExam, DraftQuestion } from '@/lib/teacher-types'
import { EXAM_TYPE_OPTIONS, DIFFICULTY_OPTIONS } from '@/lib/teacher-types'

const QTYPE_LABELS = {
  trac_nghiem: 'Trắc nghiệm',
  dung_sai:    'Đúng/Sai',
  tu_luan:     'Tự luận',
}

const QTYPE_COLORS = {
  trac_nghiem: 'bg-blue-50 text-blue-700',
  dung_sai:    'bg-purple-50 text-purple-700',
  tu_luan:     'bg-orange-50 text-orange-700',
}

function PublishModal({
  draft,
  onPublish,
  onClose,
}: {
  draft: DraftExam
  onPublish: (opts: { title: string; exam_year: number; exam_type: string }) => Promise<void>
  onClose: () => void
}) {
  const [title, setTitle] = useState(draft.title)
  const [year, setYear] = useState(String(draft.exam_year))
  const [type, setType] = useState(draft.exam_type)
  const [loading, setLoading] = useState(false)

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl p-6 w-full max-w-md card-shadow">
        <h3 className="font-bold text-navy text-lg mb-4">Đăng đề thi</h3>
        <div className="flex flex-col gap-3">
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">Tên đề</label>
            <input value={title} onChange={e => setTitle(e.target.value)}
              className="w-full px-3 py-2 border-2 border-gray-200 rounded-xl text-sm focus:outline-none focus:border-navy" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1">Năm</label>
              <input type="number" value={year} onChange={e => setYear(e.target.value)}
                className="w-full px-3 py-2 border-2 border-gray-200 rounded-xl text-sm focus:outline-none focus:border-navy" />
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1">Loại đề</label>
              <select value={type} onChange={e => setType(e.target.value)}
                className="w-full px-3 py-2 border-2 border-gray-200 rounded-xl text-sm focus:outline-none focus:border-navy bg-white">
                {EXAM_TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
          </div>
        </div>
        <div className="flex gap-2 mt-5">
          <button onClick={onClose} className="flex-1 px-4 py-2 border border-gray-200 rounded-xl text-sm text-gray-600 hover:bg-gray-50">Hủy</button>
          <button
            disabled={loading || !title.trim()}
            onClick={async () => {
              setLoading(true)
              await onPublish({ title, exam_year: parseInt(year), exam_type: type })
              setLoading(false)
            }}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-navy text-white rounded-xl text-sm font-semibold hover:bg-navy-dark disabled:opacity-60"
          >
            <Send size={15} />
            {loading ? 'Đang đăng...' : 'Đăng đề'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function DraftEditorPage() {
  const { id } = useParams() as { id: string }
  const router = useRouter()

  const [draft, setDraft] = useState<DraftExam | null>(null)
  const [questions, setQuestions] = useState<DraftQuestion[]>([])
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editBuffer, setEditBuffer] = useState<Partial<DraftQuestion>>({})
  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState('')
  const [showPublish, setShowPublish] = useState(false)
  const [publishedExamId, setPublishedExamId] = useState<number | null>(null)
  const [showAddMenu, setShowAddMenu] = useState(false)
  const [includeSolutions, setIncludeSolutions] = useState(false)

  const load = useCallback(async () => {
    const res = await fetch(`/api/teacher/drafts/${id}`)
    if (!res.ok) return
    const d: DraftExam = await res.json()
    setDraft(d)
    setQuestions((d.draft_questions || []) as DraftQuestion[])
  }, [id])

  useEffect(() => { load() }, [load])

  const startEdit = (q: DraftQuestion) => {
    setEditingId(q.id)
    setEditBuffer({ ...q })
  }

  const cancelEdit = () => {
    setEditingId(null)
    setEditBuffer({})
  }

  const saveQuestion = async () => {
    if (!editingId) return
    setSaving(true)
    const res = await fetch(`/api/teacher/drafts/${id}/questions/${editingId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(editBuffer),
    })
    if (res.ok) {
      setQuestions(prev => prev.map(q => q.id === editingId ? { ...q, ...editBuffer } as DraftQuestion : q))
      setSaveMsg('Đã lưu')
      setTimeout(() => setSaveMsg(''), 2000)
    }
    setSaving(false)
    setEditingId(null)
    setEditBuffer({})
  }

  const deleteQuestion = async (qid: string) => {
    if (!confirm('Xóa câu hỏi này?')) return
    await fetch(`/api/teacher/drafts/${id}/questions/${qid}`, { method: 'DELETE' })
    setQuestions(prev => prev.filter(q => q.id !== qid))
  }

  const addQuestion = async (type: DraftQuestion['question_type']) => {
    const res = await fetch(`/api/teacher/drafts/${id}/questions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question_type: type }),
    })
    if (!res.ok) return
    const newQ: DraftQuestion = await res.json()
    setQuestions(prev => [...prev, newQ])
    setEditingId(newQ.id)
    setEditBuffer({ ...newQ })
  }

  const handlePublish = async (opts: { title: string; exam_year: number; exam_type: string }) => {
    const res = await fetch(`/api/teacher/drafts/${id}/publish`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(opts),
    })
    const data = await res.json()
    if (data.error) { alert('Lỗi: ' + data.error); return }
    setPublishedExamId(data.examId)
    setShowPublish(false)
    load()
  }

  if (!draft) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-navy/30 border-t-navy rounded-full animate-spin" />
      </div>
    )
  }
  const sortedQuestions = [...questions].sort((a, b) => (a.question_number ?? 0) - (b.question_number ?? 0))
  const p1 = sortedQuestions.filter(q => q.question_type === 'trac_nghiem')
  const p2 = sortedQuestions.filter(q => q.question_type === 'dung_sai')
  const p3 = sortedQuestions.filter(q => q.question_type === 'tu_luan')

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Link href="/teacher/dashboard" className="text-gray-400 hover:text-navy transition-colors no-print">
            <ArrowLeft size={20} />
          </Link>
          <div>
            <h1 className="text-xl font-black text-navy">{draft.title}</h1>
            <p className="text-sm text-gray-400">{questions.length} câu hỏi · {draft.status === 'published' ? '✅ Đã đăng' : 'Đang soạn'}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 no-print">
          {/* Checkbox kèm lời giải */}
          <label className="flex items-center gap-1.5 text-xs text-gray-500 font-semibold cursor-pointer select-none border border-gray-200 px-3 py-2 rounded-xl hover:bg-gray-50">
            <input
              type="checkbox"
              checked={includeSolutions}
              onChange={e => setIncludeSolutions(e.target.checked)}
              className="rounded border-gray-300 text-navy focus:ring-navy cursor-pointer"
            />
            Kèm lời giải & ĐA
          </label>

          {/* Nút In đề thi */}
          <button
            onClick={() => window.print()}
            className="flex items-center gap-2 px-3 py-2 border border-gray-200 text-gray-600 text-sm font-semibold rounded-xl hover:bg-gray-50"
          >
            <Printer size={15} /> In đề (PDF)
          </button>

          {saveMsg && <span className="text-green-600 text-sm flex items-center gap-1"><CheckCircle size={14} />{saveMsg}</span>}
          {draft.status === 'published' && publishedExamId && (
            <Link href={`/exams/${publishedExamId}`} target="_blank"
              className="flex items-center gap-2 px-3 py-2 bg-navy/10 text-navy text-sm font-semibold rounded-xl hover:bg-navy/20">
              <Eye size={15} /> Xem đề
            </Link>
          )}
          {draft.status !== 'published' && (
            <div className="relative">
              <button
                onClick={() => setShowAddMenu(v => !v)}
                className="flex items-center gap-2 px-3 py-2 border border-gray-200 text-gray-600 text-sm font-semibold rounded-xl hover:bg-gray-50"
              >
                <Plus size={15} /> Thêm câu
              </button>
              {showAddMenu && (
                <div className="absolute right-0 top-full mt-1 bg-white border border-gray-200 rounded-xl card-shadow z-10 min-w-40 overflow-hidden">
                  {(['trac_nghiem', 'dung_sai', 'tu_luan'] as const).map(t => (
                    <button
                      key={t}
                      onClick={() => { addQuestion(t); setShowAddMenu(false) }}
                      className="w-full text-left px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50"
                    >
                      {t === 'trac_nghiem' ? 'Trắc nghiệm' : t === 'dung_sai' ? 'Đúng/Sai' : 'Tự luận'}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
          {draft.status !== 'published' && (
            <button
              onClick={() => setShowPublish(true)}
              className="flex items-center gap-2 px-4 py-2 bg-navy text-white text-sm font-semibold rounded-xl hover:bg-navy-dark"
            >
              <Send size={15} /> Đăng đề
            </button>
          )}
        </div>
      </div>

      {publishedExamId && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-xl flex items-center gap-2 text-green-700 text-sm">
          <CheckCircle size={16} />
          Đề đã đăng thành công! Học sinh có thể thi tại{' '}
          <Link href={`/exams/${publishedExamId}`} target="_blank" className="underline font-semibold">/exams/{publishedExamId}</Link>
        </div>
      )}

      {/* Questions by section */}
      {[
        { label: 'Phần I — Trắc nghiệm', qs: p1, type: 'trac_nghiem' as const },
        { label: 'Phần II — Đúng/Sai', qs: p2, type: 'dung_sai' as const },
        { label: 'Phần III — Tự luận', qs: p3, type: 'tu_luan' as const },
      ].filter(s => s.qs.length > 0).map(section => (
        <section key={section.type} className="mb-6">
          <h2 className="text-sm font-bold text-navy uppercase tracking-wide mb-3 flex items-center gap-2">
            {section.label}
            <span className="font-normal text-gray-400">({section.qs.length} câu)</span>
          </h2>
          <div className="flex flex-col gap-3">
            {section.qs.map((q, idx) => (
              <QuestionCard
                key={q.id}
                q={q}
                idx={idx}
                isEditing={editingId === q.id}
                editBuffer={editBuffer}
                setEditBuffer={setEditBuffer}
                onEdit={() => startEdit(q)}
                onCancel={cancelEdit}
                onSave={saveQuestion}
                onDelete={() => deleteQuestion(q.id)}
                saving={saving}
              />
            ))}
          </div>
        </section>
      ))}

      {questions.length === 0 && (
        <div className="text-center py-12 text-gray-400">
          <AlertCircle size={32} className="mx-auto mb-2" />
          <p>Chưa có câu hỏi nào</p>
        </div>
      )}

      {/* Publish modal */}
      {showPublish && draft && (
        <PublishModal draft={draft} onPublish={handlePublish} onClose={() => setShowPublish(false)} />
      )}

      {/* CSS print style override */}
      <style dangerouslySetInnerHTML={{ __html: `
        @media print {
          /* Hide non-print elements */
          .no-print, button, a[href^="/teacher"], .no-print-important,
          .fixed.inset-y-0.left-0, /* sidebar */
          .fixed.top-0.left-0.right-0 /* top bar */ {
            display: none !important;
          }
          /* Custom margins */
          @page {
            margin: 2cm;
          }
          body, html, main, #__next, .max-w-5xl {
            background: white !important;
            color: black !important;
            padding: 0 !important;
            margin: 0 !important;
            max-width: 100% !important;
            box-shadow: none !important;
          }
          .shadow-none-print {
            box-shadow: none !important;
            border: none !important;
            padding: 0 !important;
            margin: 0 0 2rem 0 !important;
          }
          .print-avoid-break {
            page-break-inside: avoid !important;
          }
          /* Solution visibility */
          ${!includeSolutions ? `
            .solution-box, .correct-answer-badge {
              display: none !important;
            }
          ` : ''}
        }
      ` }} />
    </div>
  )
}

function QuestionCard({
  q, idx, isEditing, editBuffer, setEditBuffer, onEdit, onCancel, onSave, onDelete, saving
}: {
  q: DraftQuestion
  idx: number
  isEditing: boolean
  editBuffer: Partial<DraftQuestion>
  setEditBuffer: (b: Partial<DraftQuestion>) => void
  onEdit: () => void
  onCancel: () => void
  onSave: () => void
  onDelete: () => void
  saving: boolean
}) {
  const optionKeys = q.options ? Object.keys(q.options).sort() : []
  const editOptions = editBuffer.options ?? q.options ?? {}

  return (
    <div className={`bg-white rounded-2xl card-shadow shadow-none-print print-avoid-break overflow-hidden ${isEditing ? 'ring-2 ring-navy' : ''}`}>
      <div className="px-4 py-3 bg-gray-50 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-gray-500">Câu {idx + 1}</span>
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${QTYPE_COLORS[q.question_type]}`}>
            {QTYPE_LABELS[q.question_type]}
          </span>
          <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">{q.difficulty_level}</span>
          {q.correct_answer && (
            <span className="correct-answer-badge text-xs px-2 py-0.5 rounded-full bg-green-50 text-green-700 font-medium">
              ĐA: {q.correct_answer}
            </span>
          )}
          {q.needs_review && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-red-50 text-red-700 font-semibold flex items-center gap-1 animate-pulse no-print">
              <AlertCircle size={10} /> Cần review
            </span>
          )}
        </div>
        {!isEditing ? (
          <div className="flex gap-1 no-print">
            <button onClick={onEdit} className="px-2 py-1 text-xs text-navy bg-navy/10 rounded-lg hover:bg-navy/20">Sửa</button>
            <button onClick={onDelete} className="px-2 py-1 text-xs text-red-500 bg-red-50 rounded-lg hover:bg-red-100">
              <Trash2 size={12} />
            </button>
          </div>
        ) : (
          <div className="flex gap-1 no-print">
            <button onClick={onCancel} className="px-2 py-1 text-xs text-gray-500 border border-gray-200 rounded-lg hover:bg-gray-50">Hủy</button>
            <button onClick={onSave} disabled={saving}
              className="flex items-center gap-1 px-2 py-1 text-xs text-white bg-navy rounded-lg hover:bg-navy-dark disabled:opacity-60">
              <Save size={12} />{saving ? 'Lưu...' : 'Lưu'}
            </button>
          </div>
        )}
      </div>

      {q.needs_review && q.review_reason && (
        <div className="px-4 py-2.5 bg-red-50/50 border-b border-gray-100 flex items-center gap-2 text-xs text-red-700 font-medium no-print">
          <AlertCircle size={14} className="shrink-0 text-red-500" />
          <span><strong>Cảnh báo tự động:</strong> {q.review_reason}</span>
        </div>
      )}

      <div className="px-4 py-4">
        {isEditing ? (
          <div className="flex flex-col gap-4">
            {/* Content editor */}
            <div>
              <label className="block text-xs font-semibold text-gray-500 uppercase mb-1.5">Nội dung câu hỏi</label>
              <LatexEditor
                value={editBuffer.content ?? q.content}
                onChange={v => setEditBuffer({ ...editBuffer, content: v })}
                rows={4}
              />
            </div>

            {/* Options */}
            {(q.question_type === 'trac_nghiem' || q.question_type === 'dung_sai') && (
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1.5">Đáp án</label>
                <div className="grid grid-cols-2 gap-2">
                  {['A','B','C','D'].map(k => (
                    <div key={k} className="flex items-start gap-2">
                      <span className="text-xs font-bold text-gray-400 mt-2 w-4 shrink-0">{k}.</span>
                      <textarea
                        value={editOptions[k] ?? ''}
                        onChange={e => setEditBuffer({
                          ...editBuffer,
                          options: { ...editOptions, [k]: e.target.value }
                        })}
                        rows={2}
                        className="flex-1 px-2 py-1.5 text-xs border border-gray-200 rounded-lg resize-none focus:outline-none focus:border-navy font-mono"
                        placeholder={`Đáp án ${k}`}
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Correct answer + level */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1.5">Đáp án đúng</label>
                <input
                  value={editBuffer.correct_answer ?? q.correct_answer ?? ''}
                  onChange={e => setEditBuffer({ ...editBuffer, correct_answer: e.target.value })}
                  placeholder="A / DSDD / 1.5"
                  className="w-full px-3 py-2 text-sm border-2 border-gray-200 rounded-xl focus:outline-none focus:border-navy"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1.5">Mức độ</label>
                <select
                  value={editBuffer.difficulty_level ?? q.difficulty_level}
                  onChange={e => setEditBuffer({ ...editBuffer, difficulty_level: e.target.value })}
                  className="w-full px-3 py-2 text-sm border-2 border-gray-200 rounded-xl focus:outline-none focus:border-navy bg-white"
                >
                  {DIFFICULTY_OPTIONS.map(d => <option key={d}>{d}</option>)}
                </select>
              </div>
            </div>

            {/* Explanation editor */}
            <div className="mt-3">
              <label className="block text-xs font-semibold text-gray-500 uppercase mb-1.5">Hướng dẫn giải (Lời giải chi tiết)</label>
              <LatexEditor
                value={editBuffer.explanation ?? q.explanation ?? ''}
                onChange={v => setEditBuffer({ ...editBuffer, explanation: v })}
                rows={3}
              />
            </div>
          </div>
        ) : (
          <>
            <div className="text-sm text-gray-800 leading-relaxed">
              <RenderLatex text={q.content} />
            </div>
            {optionKeys.length > 0 && (
              <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1">
                {optionKeys.map(k => (
                  <div key={k} className="flex items-start gap-1.5 text-sm">
                    <span className={`font-bold shrink-0 text-xs mt-0.5 ${q.correct_answer === k ? 'text-green-600' : 'text-gray-400'}`}>
                      {k}.
                    </span>
                    <span className={q.correct_answer === k ? 'text-green-700' : 'text-gray-700'}>
                      <RenderLatex text={q.options![k]} />
                    </span>
                  </div>
                ))}
              </div>
            )}
            
            {/* Solution/Explanation display */}
            {q.explanation && (
              <div className="solution-box mt-4 pt-3 border-t border-dashed border-gray-100">
                <span className="block text-xs font-semibold text-gray-400 uppercase mb-1.5 font-mono">Hướng dẫn giải chi tiết</span>
                <div className="text-sm text-gray-700 leading-relaxed bg-gray-50/30 p-4 rounded-xl border border-gray-100/50">
                  <RenderLatex text={q.explanation} />
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
