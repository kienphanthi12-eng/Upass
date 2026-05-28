'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import SectionNumber from '@/components/ui/SectionNumber'
import DisplayHeading from '@/components/ui/DisplayHeading'
import { CheckCircle, Search } from 'lucide-react'
import type { DraftExam } from '@/lib/teacher-types'
import { EXAM_TYPE_OPTIONS } from '@/lib/teacher-types'

function ExamTypeLabel({ type }: { type: string }) {
  const opt = EXAM_TYPE_OPTIONS.find(o => o.value === type)
  return <span className="text-xs tracking-label text-ink-50">{opt?.label ?? type}</span>
}

function AssignModal({ examId, onClose }: { examId: number; onClose: () => void }) {
  const [className, setClassName] = useState('all')
  const [loading, setLoading] = useState(false)
  const [done, setDone] = useState(false)

  const assign = async () => {
    setLoading(true)
    await fetch('/api/teacher/assign', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ exam_id: examId, assigned_to: className }),
    })
    setLoading(false)
    setDone(true)
  }

  return (
    <div className="fixed inset-0 bg-ink/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-paper border border-line p-8 w-full max-w-md">
        <p className="text-xs tracking-label text-ink-50 mb-3">Giao bài</p>
        <p className="font-display text-3xl text-ink mb-6">
          Giao bài cho <em className="italic">học sinh</em>.
        </p>
        {done ? (
          <div className="text-center py-4">
            <CheckCircle size={36} className="text-moss mx-auto mb-3" />
            <p className="font-display text-2xl text-ink italic mb-6">Đã giao thành công.</p>
            <button onClick={onClose} className="inline-flex items-center gap-2 px-6 py-3 bg-ink text-paper text-sm tracking-label hover:bg-moss">
              Đóng →
            </button>
          </div>
        ) : (
          <>
            <div className="mb-6">
              <p className="text-xs tracking-label text-ink-50 mb-2">Giao cho lớp</p>
              <input
                type="text"
                value={className}
                onChange={e => setClassName(e.target.value)}
                placeholder='10A1, 11B2, hoặc "all"'
                className="w-full bg-transparent border-0 border-b border-line py-3 text-base text-ink placeholder:text-ink-30 focus:outline-none focus:border-ink"
              />
            </div>
            <div className="flex items-center justify-between gap-4">
              <button onClick={onClose} className="text-sm tracking-label text-ink-50 link-editorial">Hủy</button>
              <button
                onClick={assign}
                disabled={loading || !className.trim()}
                className="inline-flex items-center gap-2 px-6 py-3 bg-ink text-paper text-sm tracking-label hover:bg-moss disabled:opacity-50"
              >
                {loading ? 'Đang giao…' : 'Giao bài →'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

type PublishedDraft = DraftExam & {
  published_exam_id: number
  submissionCount?: number
  exams?: { display_title: string | null }
}

export default function TeacherExamsPage() {
  const [exams, setExams] = useState<PublishedDraft[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [assigningId, setAssigningId] = useState<number | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    const drafts: DraftExam[] = await fetch('/api/teacher/drafts').then(r => r.json()).catch(() => [])
    const published = drafts.filter(d => d.status === 'published' && d.published_exam_id) as PublishedDraft[]
    setExams(published)
    setLoading(false)

    if (published.length > 0) {
      const updated = [...published]
      await Promise.all(
        published.map(async (d, i) => {
          const res = await fetch(`/api/teacher/exams/${d.published_exam_id}/submissions`).then(r => r.json()).catch(() => [])
          updated[i] = { ...d, submissionCount: Array.isArray(res) ? res.length : 0 }
        }),
      )
      setExams([...updated])
    }
  }, [])

  useEffect(() => { load() }, [load])

  const filtered = exams.filter(e => !search || e.title?.toLowerCase().includes(search.toLowerCase()))

  return (
    <div className="p-10 max-w-6xl">
      <SectionNumber n={1} label="Đề đã đăng" />
      <div className="flex items-start justify-between gap-6 flex-wrap mt-6 mb-10">
        <div>
          <DisplayHeading size="lg">
            Đề thi <em className="italic">đã xuất bản</em>.
          </DisplayHeading>
          <p className="mt-4 text-base text-ink-50">
            {loading ? '...' : `${exams.length} đề thi đang chạy.`}
          </p>
        </div>
        <Link
          href="/teacher/upload"
          className="inline-flex items-center gap-2 px-6 py-3 bg-ink text-paper text-sm tracking-label hover:bg-moss transition-colors"
        >
          Tải đề mới <span aria-hidden>→</span>
        </Link>
      </div>

      {/* Search */}
      <div className="relative mb-10 border-y border-line py-4">
        <Search size={14} className="absolute left-0 top-1/2 -translate-y-1/2 text-ink-30" />
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Tìm đề theo tên..."
          className="w-full pl-7 py-1 bg-transparent border-0 text-base text-ink placeholder:text-ink-30 focus:outline-none"
        />
      </div>

      {loading ? (
        <div className="space-y-0">
          {[1, 2, 3].map(i => (
            <div key={i} className="border-t border-line py-6 animate-pulse">
              <div className="grid grid-cols-12 gap-4">
                <div className="col-span-1 h-3 bg-line w-8" />
                <div className="col-span-7 h-5 bg-line w-2/3" />
                <div className="col-span-4 h-3 bg-line" />
              </div>
            </div>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <p className="text-center py-24 border-t border-line font-display text-3xl text-ink-50 italic">
          {search ? 'Không tìm thấy đề phù hợp.' : 'Chưa có đề nào được đăng.'}
        </p>
      ) : (
        <ul>
          {filtered.map((d, i) => (
            <li key={d.id} className="border-t border-line py-6">
              <div className="grid grid-cols-12 gap-4 items-baseline">
                <span className="col-span-2 sm:col-span-1 text-xs tracking-label text-ink-50 font-mono">
                  ({String(i + 1).padStart(2, '0')})
                </span>
                <div className="col-span-10 sm:col-span-6">
                  <h3 className="font-display text-2xl text-ink leading-snug">
                    {d.title || 'Đề thi chưa có tiêu đề'}
                    {d.exams?.display_title && (
                      <span className="text-sm font-sans font-normal text-ink-30 ml-2">
                        ({d.exams.display_title})
                      </span>
                    )}
                  </h3>
                  <p className="mt-1.5 text-xs tracking-label text-ink-50">
                    <ExamTypeLabel type={d.exam_type} /> · {d.exam_year}
                    {(d.draft_questions as unknown[])?.length > 0 && <> · {(d.draft_questions as unknown[]).length} câu</>}
                    {d.submissionCount !== undefined && <> · <span className="text-moss">{d.submissionCount} bài nộp</span></>}
                  </p>
                </div>
                <div className="col-span-12 sm:col-span-5 flex items-center gap-6 sm:justify-end flex-wrap">
                  <Link
                    href={`/teacher/exams/${d.published_exam_id}/submissions`}
                    className="text-sm tracking-label text-ink link-editorial"
                  >
                    Kết quả →
                  </Link>
                  <button
                    onClick={() => setAssigningId(d.published_exam_id)}
                    className="text-sm tracking-label text-ink link-editorial"
                  >
                    Giao bài →
                  </button>
                  <Link
                    href={`/exams/${d.published_exam_id}`}
                    target="_blank"
                    className="text-sm tracking-label text-ink-50 hover:text-ink link-editorial"
                  >
                    Xem đề →
                  </Link>
                </div>
              </div>
            </li>
          ))}
          <li className="border-t border-line" />
        </ul>
      )}

      {assigningId && (
        <AssignModal examId={assigningId} onClose={() => { setAssigningId(null); load() }} />
      )}
    </div>
  )
}
