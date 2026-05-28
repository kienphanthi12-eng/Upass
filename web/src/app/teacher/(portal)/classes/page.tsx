'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import SectionNumber from '@/components/ui/SectionNumber'
import DisplayHeading from '@/components/ui/DisplayHeading'
import { CheckCircle } from 'lucide-react'

interface ClassRow {
  class_name: string
  student_count: number
  submission_count: number
  avg_score: number
  last_submitted_at: string
}

interface DraftExam {
  id: number
  title: string
  published_exam_id: number | null
  status: string
}

function AssignModal({
  className: cls,
  exams,
  onClose,
}: {
  className: string
  exams: DraftExam[]
  onClose: () => void
}) {
  const [selectedExam, setSelectedExam] = useState<number | null>(
    exams.find(e => e.published_exam_id)?.published_exam_id ?? null
  )
  const [loading, setLoading] = useState(false)
  const [done, setDone] = useState(false)

  const assign = async () => {
    if (!selectedExam) return
    setLoading(true)
    await fetch('/api/teacher/assign', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ exam_id: selectedExam, assigned_to: cls }),
    })
    setLoading(false)
    setDone(true)
  }

  const published = exams.filter(e => e.published_exam_id)

  return (
    <div className="fixed inset-0 bg-ink/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-paper border border-line p-8 w-full max-w-md">
        <p className="text-xs tracking-label text-ink-50 mb-3">Giao bài cho lớp</p>
        <p className="font-display text-3xl text-ink mb-6">
          Lớp <em className="italic">{cls}</em>.
        </p>

        {done ? (
          <div className="text-center py-4">
            <CheckCircle size={36} className="text-moss mx-auto mb-3" />
            <p className="font-display text-2xl text-ink italic mb-6">Đã giao thành công.</p>
            <button onClick={onClose} className="inline-flex items-center gap-2 px-6 py-3 bg-ink text-paper text-sm tracking-label hover:bg-moss">
              Đóng →
            </button>
          </div>
        ) : published.length === 0 ? (
          <div className="text-center py-4">
            <p className="font-display text-2xl text-ink-50 italic mb-6">Chưa có đề nào được đăng.</p>
            <button onClick={onClose} className="text-sm tracking-label text-ink link-editorial">Đóng</button>
          </div>
        ) : (
          <>
            <div className="mb-6">
              <p className="text-xs tracking-label text-ink-50 mb-2">Chọn đề thi</p>
              <select
                value={selectedExam ?? ''}
                onChange={e => setSelectedExam(Number(e.target.value))}
                className="w-full bg-transparent border-0 border-b border-line py-3 text-base text-ink focus:outline-none focus:border-ink"
              >
                <option value="" disabled>-- Chọn đề --</option>
                {published.map(e => (
                  <option key={e.id} value={e.published_exam_id!}>
                    {e.title || `Đề #${e.published_exam_id}`}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-center justify-between gap-4">
              <button onClick={onClose} className="text-sm tracking-label text-ink-50 link-editorial">Hủy</button>
              <button
                onClick={assign}
                disabled={loading || !selectedExam}
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

export default function ClassesPage() {
  const [classes, setClasses] = useState<ClassRow[]>([])
  const [exams, setExams] = useState<DraftExam[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [assigningClass, setAssigningClass] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([
      fetch('/api/teacher/classes').then(r => r.json()),
      fetch('/api/teacher/drafts').then(r => r.json()).catch(() => []),
    ]).then(([classData, drafts]) => {
      if (Array.isArray(classData)) setClasses(classData)
      else setError(classData.error ?? 'Lỗi tải dữ liệu')
      if (Array.isArray(drafts)) setExams(drafts)
    }).catch(() => setError('Không thể tải dữ liệu lớp học'))
    .finally(() => setLoading(false))
  }, [])

  const totalStudents = classes.reduce((s, c) => s + c.student_count, 0)
  const totalSubs = classes.reduce((s, c) => s + c.submission_count, 0)
  const avgAll = classes.length > 0 && totalSubs > 0
    ? (classes.reduce((s, c) => s + c.avg_score * c.submission_count, 0) / totalSubs).toFixed(2)
    : '—'

  return (
    <div className="p-10 max-w-6xl">
      <SectionNumber n={1} label="Lớp học" />
      <DisplayHeading size="lg" className="mt-6">
        Quản lý <em className="italic">lớp học</em>.
      </DisplayHeading>

      {!loading && !error && classes.length > 0 && (
        <p className="mt-8 font-display text-xl sm:text-2xl text-ink-70 leading-relaxed max-w-3xl">
          <em className="italic text-ink">{classes.length} lớp</em>,
          <em className="italic text-ink"> {totalStudents} học sinh</em>,
          <em className="italic text-ink"> {totalSubs} lượt nộp bài</em>,
          điểm TB chung <em className="italic text-ink">{avgAll}</em>.
        </p>
      )}

      <div className="mt-16">
        {loading ? (
          <div className="space-y-6">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="border-t border-line py-6 animate-pulse">
                <div className="h-6 bg-line w-1/4 mb-2" />
                <div className="h-3 bg-line w-1/2" />
              </div>
            ))}
          </div>
        ) : error ? (
          <p className="border-l-2 border-ember pl-4 text-ember">{error}</p>
        ) : classes.length === 0 ? (
          <p className="text-center py-24 border-t border-line font-display text-3xl text-ink-50 italic">
            Chưa có dữ liệu lớp học.
          </p>
        ) : (
          <ul>
            {classes.map((cls, i) => (
              <li key={cls.class_name} className="border-t border-line py-6">
                <div className="grid grid-cols-12 gap-4 items-baseline">
                  <span className="col-span-2 sm:col-span-1 text-xs font-mono text-ink-50">
                    ({String(i + 1).padStart(2, '0')})
                  </span>
                  <div className="col-span-10 sm:col-span-4">
                    <h3 className="font-display text-3xl text-ink">{cls.class_name}</h3>
                  </div>
                  <div className="col-span-12 sm:col-span-3 sm:text-right">
                    <p className="text-xs tracking-label text-ink-50">Học sinh · Bài nộp</p>
                    <p className="font-display text-2xl text-ink mt-1">
                      {cls.student_count} <span className="text-ink-30">·</span> {cls.submission_count}
                    </p>
                  </div>
                  <div className="col-span-6 sm:col-span-2 sm:text-right">
                    <p className="text-xs tracking-label text-ink-50">Điểm TB</p>
                    <p className={`font-display text-2xl mt-1 ${
                      cls.submission_count > 0
                        ? (cls.avg_score >= 8 ? 'text-moss' : cls.avg_score >= 5 ? 'text-sun' : 'text-ember')
                        : 'text-ink-30'
                    }`}>
                      {cls.submission_count > 0 ? cls.avg_score.toFixed(1) : '—'}
                    </p>
                  </div>
                  <div className="col-span-6 sm:col-span-2 flex flex-col items-end gap-2 text-right">
                    <Link
                      href={`/teacher/students?class=${encodeURIComponent(cls.class_name)}`}
                      className="text-sm tracking-label text-ink link-editorial"
                    >
                      Học sinh →
                    </Link>
                    <button
                      onClick={() => setAssigningClass(cls.class_name)}
                      className="text-sm tracking-label text-ink link-editorial"
                    >
                      Giao bài →
                    </button>
                  </div>
                </div>
              </li>
            ))}
            <li className="border-t border-line" />
          </ul>
        )}
      </div>

      {assigningClass && (
        <AssignModal
          className={assigningClass}
          exams={exams}
          onClose={() => setAssigningClass(null)}
        />
      )}
    </div>
  )
}
