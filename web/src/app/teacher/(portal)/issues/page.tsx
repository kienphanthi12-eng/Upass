'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import SectionNumber from '@/components/ui/SectionNumber'
import DisplayHeading from '@/components/ui/DisplayHeading'

interface IssueRow {
  id: number
  question_id: number
  reported_by: string | null
  reporter_role: 'student' | 'teacher' | 'admin' | 'guest' | null
  note: string
  status: 'open' | 'resolved' | 'dismissed'
  created_at: string
  resolved_at: string | null
  questions?: {
    id: number
    content: string
    question_number: number | null
    exam_id: number
    exams?: {
      id: number
      title: string
      display_title: string | null
      year: number
    }
  }
}

function formatDate(ts: string) {
  return new Date(ts).toLocaleString('vi-VN', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function stripLatex(text: string): string {
  if (!text) return ''
  return text
    .replace(/\$\$[\s\S]*?\$\$/g, '[công thức]')
    .replace(/\$[^$]*\$/g, '[ct]')
    .replace(/!\[[^\]]*\]\([^)]+\)/g, '[hình]')
    .replace(/<[^>]+>/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 200)
}

const STATUS_LABELS = {
  open: 'Đang mở',
  resolved: 'Đã sửa',
  dismissed: 'Bỏ qua',
}

const ROLE_LABELS = {
  student: 'Học sinh',
  teacher: 'Giáo viên',
  admin: 'Admin',
  guest: 'Khách',
}

export default function IssuesPage() {
  const [issues, setIssues] = useState<IssueRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [statusFilter, setStatusFilter] = useState<'open' | 'resolved' | 'dismissed'>('open')

  const load = useCallback(async (status: 'open' | 'resolved' | 'dismissed') => {
    setLoading(true)
    try {
      const res = await fetch(`/api/teacher/issues?status=${status}`)
      const data = await res.json()
      if (Array.isArray(data)) {
        setIssues(data)
        setError('')
      } else {
        setError(data.error ?? 'Lỗi tải dữ liệu')
      }
    } catch {
      setError('Không thể tải danh sách báo lỗi')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load(statusFilter) }, [statusFilter, load])

  const updateStatus = async (issueId: number, newStatus: 'resolved' | 'dismissed' | 'open') => {
    await fetch(`/api/teacher/issues/${issueId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus }),
    })
    // Refresh
    load(statusFilter)
  }

  const openCount = issues.length

  return (
    <div className="p-10 max-w-6xl">
      <SectionNumber n={1} label="Báo lỗi" />
      <DisplayHeading size="lg" className="mt-6">
        Câu hỏi <em className="italic">cần kiểm tra</em>.
      </DisplayHeading>

      <p className="mt-8 font-display text-xl sm:text-2xl text-ink-70 leading-relaxed max-w-3xl">
        {statusFilter === 'open'
          ? <><em className="italic text-ink">{openCount} báo lỗi</em> đang chờ xử lý.</>
          : statusFilter === 'resolved'
          ? <><em className="italic text-ink">{openCount} báo lỗi</em> đã được sửa.</>
          : <><em className="italic text-ink">{openCount} báo lỗi</em> đã bỏ qua.</>
        }
      </p>

      {/* Filter tabs */}
      <div className="mt-12 border-y border-line py-4 flex items-center gap-6 flex-wrap">
        <span className="text-xs tracking-label text-ink-50">Trạng thái</span>
        {(['open', 'resolved', 'dismissed'] as const).map(s => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`text-sm tracking-label transition-colors ${
              statusFilter === s ? 'text-ink' : 'text-ink-30 hover:text-ink'
            }`}
          >
            {STATUS_LABELS[s]}
          </button>
        ))}
      </div>

      <div className="mt-12">
        {loading ? (
          <div className="space-y-0">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="border-t border-line py-6 animate-pulse">
                <div className="h-3 bg-line w-1/4 mb-2" />
                <div className="h-5 bg-line w-2/3 mb-2" />
                <div className="h-3 bg-line w-1/2" />
              </div>
            ))}
          </div>
        ) : error ? (
          <p className="border-l-2 border-ember pl-4 text-ember">{error}</p>
        ) : issues.length === 0 ? (
          <p className="text-center py-24 border-t border-line font-display text-3xl text-ink-50 italic">
            {statusFilter === 'open' ? 'Không có báo lỗi nào đang mở. 🎉' : 'Không có báo lỗi nào ở trạng thái này.'}
          </p>
        ) : (
          <ul>
            {issues.map((issue, i) => {
              const exam = issue.questions?.exams
              const examName = exam ? (exam.display_title || exam.title || `Đề #${exam.id}`) : '—'
              const qSnippet = stripLatex(issue.questions?.content ?? '')

              return (
                <li key={issue.id} className="border-t border-line py-7">
                  <div className="grid grid-cols-12 gap-4">
                    {/* Index */}
                    <span className="col-span-2 sm:col-span-1 text-xs font-mono text-ink-50">
                      ({String(i + 1).padStart(2, '0')})
                    </span>

                    {/* Content */}
                    <div className="col-span-10 sm:col-span-8">
                      <div className="flex items-center gap-4 flex-wrap mb-3">
                        <span className="font-display text-2xl text-ink italic">{examName}</span>
                        {issue.questions?.question_number != null && (
                          <span className="text-xs tracking-label text-ink-50">
                            · Câu {issue.questions.question_number}
                          </span>
                        )}
                        <span className="text-xs tracking-label text-ink-50">
                          · {issue.reporter_role ? ROLE_LABELS[issue.reporter_role] : 'Ẩn danh'}
                        </span>
                        <span className="text-xs tracking-label text-ink-50">
                          · {formatDate(issue.created_at)}
                        </span>
                      </div>

                      {/* Question snippet */}
                      {qSnippet && (
                        <p className="text-sm text-ink-50 mb-3 leading-relaxed border-l-2 border-line pl-4">
                          {qSnippet}{qSnippet.length >= 200 ? '…' : ''}
                        </p>
                      )}

                      {/* Report note */}
                      <p className="text-base text-ink leading-relaxed border-l-2 border-ember pl-4 italic font-display">
                        &ldquo;{issue.note}&rdquo;
                      </p>
                    </div>

                    {/* Actions */}
                    <div className="col-span-12 sm:col-span-3 flex flex-col items-end gap-2 text-right">
                      {exam && (
                        <Link
                          href={`/exams/${exam.id}`}
                          target="_blank"
                          className="text-xs tracking-label text-ink-50 hover:text-ink link-editorial"
                        >
                          Xem đề →
                        </Link>
                      )}

                      {issue.status === 'open' ? (
                        <>
                          <button
                            onClick={() => updateStatus(issue.id, 'resolved')}
                            className="text-sm tracking-label text-moss hover:text-ink link-editorial"
                          >
                            Đánh dấu đã sửa →
                          </button>
                          <button
                            onClick={() => updateStatus(issue.id, 'dismissed')}
                            className="text-xs tracking-label text-ink-30 hover:text-ink link-editorial"
                          >
                            Bỏ qua
                          </button>
                        </>
                      ) : (
                        <button
                          onClick={() => updateStatus(issue.id, 'open')}
                          className="text-sm tracking-label text-ink-50 hover:text-ink link-editorial"
                        >
                          Mở lại →
                        </button>
                      )}
                    </div>
                  </div>
                </li>
              )
            })}
            <li className="border-t border-line" />
          </ul>
        )}
      </div>
    </div>
  )
}
