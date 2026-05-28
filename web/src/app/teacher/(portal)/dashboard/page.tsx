'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import SectionNumber from '@/components/ui/SectionNumber'
import DisplayHeading from '@/components/ui/DisplayHeading'
import { CheckCircle } from 'lucide-react'
import type { DraftExam, Assignment } from '@/lib/teacher-types'
import { EXAM_TYPE_OPTIONS } from '@/lib/teacher-types'

function ExamTypeLabel({ type }: { type: string }) {
  const opt = EXAM_TYPE_OPTIONS.find(o => o.value === type)
  return <span className="text-xs tracking-label text-ink-50">{opt?.label ?? type}</span>
}

function AssignModal({
  examId,
  onClose,
}: {
  examId: number
  onClose: () => void
}) {
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
              <p className="text-xs text-ink-30 mt-2">Nhập &quot;all&quot; để giao cho tất cả học sinh.</p>
            </div>
            <div className="flex items-center justify-between gap-4">
              <button
                onClick={onClose}
                className="text-sm tracking-label text-ink-50 link-editorial"
              >
                Hủy
              </button>
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

export default function TeacherDashboard() {
  const router = useRouter()
  const [creating, setCreating] = useState(false)
  const [drafts, setDrafts] = useState<(DraftExam & { ocr_jobs?: { filename: string; status: string } })[]>([])
  const [assignments, setAssignments] = useState<(Assignment & { exams?: { title: string; year: number; exam_type: string } })[]>([])
  const [submissionCounts, setSubmissionCounts] = useState<Record<number, number>>({})
  const [loading, setLoading] = useState(true)
  const [assigningExamId, setAssigningExamId] = useState<number | null>(null)

  const handleCreateBlank = async () => {
    setCreating(true)
    try {
      const res = await fetch('/api/teacher/drafts', { method: 'POST' })
      const data = await res.json()
      if (data.id) {
        router.push(`/teacher/drafts/${data.id}`)
      } else {
        alert(data.error || 'Có lỗi xảy ra khi tạo đề')
      }
    } catch (e) {
      alert('Lỗi kết nối')
    } finally {
      setCreating(false)
    }
  }

  const load = useCallback(async () => {
    const [draftsRes, assignRes] = await Promise.all([
      fetch('/api/teacher/drafts').then(r => r.json()),
      fetch('/api/teacher/assign').then(r => r.json()),
    ])
    const draftsData: DraftExam[] = Array.isArray(draftsRes) ? draftsRes : []
    setDrafts(draftsData)
    setAssignments(Array.isArray(assignRes) ? assignRes : [])
    setLoading(false)

    const publishedIds = draftsData
      .filter(d => d.status === 'published' && d.published_exam_id)
      .map(d => d.published_exam_id!)
    if (publishedIds.length > 0) {
      const counts: Record<number, number> = {}
      await Promise.all(publishedIds.map(async eid => {
        const res = await fetch(`/api/teacher/exams/${eid}/submissions`).then(r => r.json()).catch(() => [])
        counts[eid] = Array.isArray(res) ? res.length : 0
      }))
      setSubmissionCounts(counts)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const published = drafts.filter(d => d.status === 'published')
  const inProgress = drafts.filter(d => d.status === 'draft')

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="font-display text-3xl text-ink-50 italic">Đang tải…</p>
      </div>
    )
  }

  return (
    <div className="p-10 max-w-6xl">
      <SectionNumber n={1} label="Tổng quan" />
      <div className="flex items-start justify-between gap-6 flex-wrap mt-6">
        <DisplayHeading size="lg">
          Bảng <em className="italic">điều khiển</em>.
        </DisplayHeading>
        <div className="flex items-center gap-3">
          <button
            onClick={handleCreateBlank}
            disabled={creating}
            className="inline-flex items-center gap-2 px-6 py-3 border border-ink text-ink text-sm tracking-label hover:bg-paper-soft transition-colors cursor-pointer disabled:opacity-50"
          >
            {creating ? 'Đang tạo…' : 'Tự soạn đề mới ✍️'}
          </button>
          <Link
            href="/teacher/upload"
            className="inline-flex items-center gap-2 px-6 py-3 bg-ink text-paper text-sm tracking-label hover:bg-moss transition-colors"
          >
            Tải đề mới <span aria-hidden>→</span>
          </Link>
        </div>
      </div>

      {/* Inline stats prose */}
      <p className="mt-10 font-display text-xl sm:text-2xl text-ink-70 leading-relaxed max-w-3xl">
        <em className="italic text-ink">{published.length} đề đã đăng</em> ·
        <em className="italic text-ink"> {inProgress.length} đề đang soạn</em> ·
        <em className="italic text-ink"> {assignments.length} bài đã giao</em>.
      </p>

      {/* Draft exams */}
      <section className="mt-16">
        <SectionNumber n={2} label="Đề đang soạn" />
        {inProgress.length === 0 ? (
          <p className="mt-6 text-base text-ink-50 italic font-display text-2xl border-t border-line pt-8">
            Chưa có đề nào đang soạn.{' '}
            <Link href="/teacher/upload" className="link-editorial text-ink not-italic">
              Tải đề PDF mới →
            </Link>
          </p>
        ) : (
          <ul className="mt-6">
            {inProgress.map(d => (
              <li key={d.id} className="border-t border-line py-6">
                <div className="flex items-baseline justify-between gap-4 flex-wrap">
                  <div>
                    <h3 className="font-display text-2xl text-ink">{d.title}</h3>
                    <p className="mt-1 text-xs tracking-label text-ink-50">
                      <ExamTypeLabel type={d.exam_type} /> · {d.exam_year} · {(d.draft_questions as unknown[])?.length ?? 0} câu
                    </p>
                  </div>
                  <Link
                    href={`/teacher/drafts/${d.id}`}
                    className="text-sm tracking-label text-ink link-editorial"
                  >
                    Chỉnh sửa →
                  </Link>
                </div>
              </li>
            ))}
            <li className="border-t border-line" />
          </ul>
        )}
      </section>

      {/* Published */}
      <section className="mt-16">
        <SectionNumber n={3} label="Đề đã đăng" />
        {published.length === 0 ? (
          <p className="mt-6 text-base text-ink-50 font-display text-2xl italic border-t border-line pt-8">
            Chưa có đề nào được đăng.
          </p>
        ) : (
          <ul className="mt-6">
            {published.map(d => (
              <li key={d.id} className="border-t border-line py-6">
                <div className="grid grid-cols-12 gap-4 items-baseline">
                  <div className="col-span-12 md:col-span-7">
                    <h3 className="font-display text-2xl text-ink">
                      {d.title}
                      {(d as any).exams?.display_title && (
                        <span className="text-sm font-sans font-normal text-ink-30 ml-2">
                          ({(d as any).exams.display_title})
                        </span>
                      )}
                    </h3>
                    <p className="mt-1 text-xs tracking-label text-ink-50">
                      <ExamTypeLabel type={d.exam_type} /> · {d.exam_year}
                      {d.published_exam_id && submissionCounts[d.published_exam_id] !== undefined && (
                        <> · {submissionCounts[d.published_exam_id]} bài nộp</>
                      )}
                    </p>
                  </div>
                  {d.published_exam_id && (
                    <div className="col-span-12 md:col-span-5 flex items-center gap-6 md:justify-end flex-wrap">
                      <Link
                        href={`/teacher/exams/${d.published_exam_id}/submissions`}
                        className="text-sm tracking-label text-ink link-editorial"
                      >
                        Kết quả →
                      </Link>
                      <button
                        onClick={() => setAssigningExamId(d.published_exam_id!)}
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
                  )}
                </div>
              </li>
            ))}
            <li className="border-t border-line" />
          </ul>
        )}
      </section>

      {assigningExamId && (
        <AssignModal
          examId={assigningExamId}
          onClose={() => { setAssigningExamId(null); load() }}
        />
      )}
    </div>
  )
}
