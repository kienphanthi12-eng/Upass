'use client'

import { useState, useEffect, useMemo } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import SectionNumber from '@/components/ui/SectionNumber'
import DisplayHeading from '@/components/ui/DisplayHeading'
import { Search } from 'lucide-react'

interface StudentRow {
  student_id: string
  full_name: string
  class_name: string | null
  student_code: string | null
  exam_count: number
  avg_score: number
  last_submitted_at: string | null
}

function scoreColor(s: number) {
  if (s >= 8) return 'text-moss'
  if (s >= 5) return 'text-sun'
  return 'text-ember'
}

function formatDate(ts: string) {
  return new Date(ts).toLocaleString('vi-VN', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

export default function StudentsPage() {
  const searchParams = useSearchParams()
  const [students, setStudents] = useState<StudentRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [classFilter, setClassFilter] = useState(searchParams.get('class') ?? '')
  const [statusFilter, setStatusFilter] = useState('')

  useEffect(() => {
    fetch('/api/teacher/students')
      .then(r => r.json())
      .then(data => {
        if (Array.isArray(data)) setStudents(data)
        else setError(data.error ?? 'Lỗi tải dữ liệu')
      })
      .catch(() => setError('Không thể tải dữ liệu học sinh'))
      .finally(() => setLoading(false))
  }, [])

  const classes = useMemo(() => {
    const set = new Set(students.map(s => s.class_name ?? 'Chưa phân lớp'))
    return Array.from(set).sort((a, b) => a.localeCompare(b, 'vi'))
  }, [students])

  const filtered = useMemo(() => {
    return students.filter(s => {
      const matchSearch = !search ||
        s.full_name.toLowerCase().includes(search.toLowerCase()) ||
        (s.student_code?.toLowerCase().includes(search.toLowerCase()) ?? false)
      const matchClass = !classFilter ||
        (s.class_name ?? 'Chưa phân lớp') === classFilter
      const matchStatus = !statusFilter ||
        (statusFilter === 'taken' ? s.exam_count > 0 : s.exam_count === 0)
      return matchSearch && matchClass && matchStatus
    })
  }, [students, search, classFilter, statusFilter])

  const examTakers = useMemo(() => students.filter(s => s.exam_count > 0), [students])

  const avgAll = useMemo(() => {
    return examTakers.length > 0
      ? (examTakers.reduce((s, r) => s + r.avg_score, 0) / examTakers.length).toFixed(2)
      : '—'
  }, [examTakers])

  return (
    <div className="p-10 max-w-6xl">
      <SectionNumber n={1} label="Học sinh" />
      <DisplayHeading size="lg" className="mt-6">
        Quản lý <em className="italic">học sinh</em>.
      </DisplayHeading>

      {!loading && !error && (
        <p className="mt-8 font-display text-xl sm:text-2xl text-ink-70 leading-relaxed max-w-3xl">
          <em className="italic text-ink">{students.length} học sinh</em> đã đăng ký,{' '}
          trong đó <em className="italic text-ink">{examTakers.length} học sinh</em> đã làm bài,{' '}
          chia thành <em className="italic text-ink">{classes.length} lớp</em>,{' '}
          điểm TB chung <em className="italic text-ink">{avgAll}</em>.
        </p>
      )}

      {/* Search + filter */}
      <div className="mt-12 border-y border-line py-4 flex flex-col sm:flex-row gap-4 sm:items-center">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-0 top-1/2 -translate-y-1/2 text-ink-30" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Tìm tên hoặc mã học sinh..."
            className="w-full pl-7 py-1 bg-transparent border-0 text-base text-ink placeholder:text-ink-30 focus:outline-none"
          />
        </div>
        <div className="flex flex-wrap items-center gap-6">
          <div className="flex items-center gap-2">
            <span className="text-xs tracking-label text-ink-50">Lớp</span>
            <select
              value={classFilter}
              onChange={e => setClassFilter(e.target.value)}
              className="bg-transparent border-0 text-sm tracking-label text-ink focus:outline-none cursor-pointer"
            >
              <option value="">Tất cả</option>
              {classes.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs tracking-label text-ink-50">Trạng thái</span>
            <select
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value)}
              className="bg-transparent border-0 text-sm tracking-label text-ink focus:outline-none cursor-pointer"
            >
              <option value="">Tất cả</option>
              <option value="taken">Đã thi</option>
              <option value="not_taken">Chưa thi</option>
            </select>
          </div>
        </div>
      </div>

      {(search || classFilter || statusFilter) && !loading && (
        <p className="mt-4 text-xs tracking-label text-ink-50">
          {filtered.length} / {students.length} học sinh
        </p>
      )}

      <div className="mt-8">
        {loading ? (
          <div className="space-y-0">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="border-t border-line py-5 animate-pulse">
                <div className="grid grid-cols-12 gap-4">
                  <div className="col-span-1 h-3 bg-line w-8" />
                  <div className="col-span-5 h-4 bg-line w-2/3" />
                  <div className="col-span-2 h-3 bg-line" />
                  <div className="col-span-2 h-3 bg-line" />
                  <div className="col-span-2 h-3 bg-line" />
                </div>
              </div>
            ))}
          </div>
        ) : error ? (
          <p className="border-l-2 border-ember pl-4 text-ember">{error}</p>
        ) : filtered.length === 0 ? (
          <p className="text-center py-24 border-t border-line font-display text-3xl text-ink-50 italic">
            {search || classFilter || statusFilter ? 'Không tìm thấy học sinh phù hợp.' : 'Chưa có học sinh nào đăng ký.'}
          </p>
        ) : (
          <div>
            <div className="grid grid-cols-12 gap-4 text-xs tracking-label text-ink-50 pb-3 border-b border-line">
              <span className="col-span-1">#</span>
              <span className="col-span-4">Học sinh</span>
              <span className="col-span-2">Lớp</span>
              <span className="col-span-1 text-right">Đề</span>
              <span className="col-span-2 text-right">Điểm TB</span>
              <span className="col-span-2 text-right">Hoạt động cuối</span>
            </div>
            {filtered.map((s, i) => (
              <div key={s.student_id} className="grid grid-cols-12 gap-4 py-4 border-b border-line items-baseline">
                <span className="col-span-1 text-xs font-mono text-ink-50">
                  ({String(i + 1).padStart(2, '0')})
                </span>
                <div className="col-span-4">
                  <Link href={`/teacher/students/${s.student_id}`} className="hover:underline hover:italic">
                    <p className="font-display text-xl text-ink inline-block">{s.full_name}</p>
                  </Link>
                  {s.student_code && (
                    <p className="text-xs tracking-label text-ink-30 mt-0.5">{s.student_code}</p>
                  )}
                </div>
                <span className="col-span-2 text-sm text-ink-50">
                  {s.class_name ?? '—'}
                </span>
                <span className="col-span-1 text-right text-base text-ink tabular-nums">{s.exam_count}</span>
                <span className={`col-span-2 text-right text-base tabular-nums ${s.exam_count > 0 ? scoreColor(s.avg_score) : 'text-ink-30'}`}>
                  {s.exam_count > 0 ? s.avg_score.toFixed(2) : '—'}
                </span>
                <span className="col-span-2 text-right text-xs text-ink-50">
                  {s.last_submitted_at ? formatDate(s.last_submitted_at) : 'Chưa thi'}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
