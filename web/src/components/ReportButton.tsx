'use client'

import { useState } from 'react'
import { Flag, CheckCircle, X } from 'lucide-react'

/**
 * Report a question as buggy — appears inline on each question.
 * Anyone (auth or guest) can submit a free-text note.
 */
export default function ReportButton({ questionId }: { questionId: number }) {
  const [open, setOpen] = useState(false)
  const [note, setNote] = useState('')
  const [loading, setLoading] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')

  const submit = async () => {
    if (note.trim().length < 3) {
      setError('Ghi chú phải có ít nhất 3 ký tự')
      return
    }
    setLoading(true)
    setError('')
    const res = await fetch(`/api/questions/${questionId}/report`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ note: note.trim() }),
    })
    const data = await res.json().catch(() => ({}))
    setLoading(false)
    if (!res.ok) {
      setError(data?.error ?? 'Gửi báo lỗi thất bại')
      return
    }
    setDone(true)
    setTimeout(() => {
      setOpen(false)
      setDone(false)
      setNote('')
    }, 1600)
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs tracking-label text-ember-bg-fg border border-ember/30 bg-ember-bg/40 hover:bg-ember hover:text-paper transition-colors rounded-sm"
        title="Câu hỏi này có lỗi? Báo cho giáo viên"
        style={{ color: '#b54a2b' }}
      >
        <Flag size={12} strokeWidth={2.2} /> BÁO LỖI
      </button>

      {open && (
        <div className="fixed inset-0 bg-ink/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-paper border border-line p-8 w-full max-w-md relative">
            <button
              onClick={() => { setOpen(false); setError(''); setNote('') }}
              className="absolute top-4 right-4 text-ink-50 hover:text-ink"
            >
              <X size={18} />
            </button>

            {done ? (
              <div className="text-center py-6">
                <CheckCircle size={36} className="text-moss mx-auto mb-3" />
                <p className="font-display text-2xl text-ink italic">Đã ghi nhận.</p>
                <p className="text-sm text-ink-50 mt-2">Cảm ơn bạn đã báo lỗi.</p>
              </div>
            ) : (
              <>
                <p className="text-xs tracking-label text-ink-50 mb-3">Báo lỗi câu hỏi</p>
                <p className="font-display text-3xl text-ink mb-2">
                  Câu này <em className="italic">có vấn đề</em>?
                </p>
                <p className="text-sm text-ink-50 mb-6">
                  Mô tả ngắn gọn — giáo viên sẽ kiểm tra và sửa.
                </p>

                {error && (
                  <p className="border-l-2 border-ember pl-3 text-sm text-ember mb-4">{error}</p>
                )}

                <textarea
                  value={note}
                  onChange={e => setNote(e.target.value)}
                  rows={4}
                  maxLength={1000}
                  placeholder="Ví dụ: Đáp án đúng phải là B chứ không phải A; công thức ở câu hỏi bị lỗi; thiếu hình ảnh..."
                  className="w-full bg-transparent border border-line p-3 text-base text-ink placeholder:text-ink-30 focus:outline-none focus:border-ink resize-none"
                />
                <p className="text-xs text-ink-30 mt-1 text-right">{note.length}/1000</p>

                <div className="flex items-center justify-between mt-6 gap-4">
                  <button
                    onClick={() => { setOpen(false); setNote(''); setError('') }}
                    className="text-sm tracking-label text-ink-50 link-editorial"
                  >
                    Hủy
                  </button>
                  <button
                    onClick={submit}
                    disabled={loading || note.trim().length < 3}
                    className="inline-flex items-center gap-2 px-6 py-3 bg-ink text-paper text-sm tracking-label hover:bg-ember disabled:opacity-50 transition-colors"
                  >
                    {loading ? 'Đang gửi…' : 'Gửi báo lỗi →'}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </>
  )
}
