'use client'

import { useState, useRef, useCallback, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Upload, FileText, AlertCircle } from 'lucide-react'
import type { OcrJobStatus } from '@/lib/teacher-types'

type Phase = 'idle' | 'uploading' | 'polling' | 'normalizing' | 'normalized' | 'extracting' | 'done' | 'error'

/* ---------- Messages while waiting (no pipeline details) ---------- */
const WAITING_MESSAGES = [
  'Đang đọc tài liệu của bạn...',
  'Phân tích nội dung bài thi...',
  'Nhận diện công thức toán học...',
  'Xử lý bảng biểu và hình ảnh...',
  'Chuẩn hóa câu hỏi...',
  'Sắp xong rồi! ✨',
]

/* ---------- Owl character ---------- */
function OwlWaiting({ done }: { done: boolean }) {
  const [msgIdx, setMsgIdx] = useState(0)

  useEffect(() => {
    if (done) return
    const t = setInterval(() => setMsgIdx(i => (i + 1) % WAITING_MESSAGES.length), 3200)
    return () => clearInterval(t)
  }, [done])

  /* Star positions around the owl */
  const stars = [
    { x: 14,  y: 22,  delay: 0,    size: 13, dur: 2.1 },
    { x: 194, y: 15,  delay: 0.55, size: 10, dur: 2.4 },
    { x: 202, y: 118, delay: 1.1,  size: 12, dur: 1.9 },
    { x: 6,   y: 125, delay: 1.75, size: 9,  dur: 2.6 },
    { x: 98,  y: 4,   delay: 0.35, size: 8,  dur: 2.2 },
    { x: 178, y: 62,  delay: 2.0,  size: 11, dur: 1.8 },
  ]

  return (
    <div className="flex flex-col items-center pt-8 pb-6 select-none">
      {/* Container holds stars + owl */}
      <div className="relative" style={{ width: 230, height: 195 }}>

        {/* ── Twinkling gold stars ── */}
        {stars.map((s, i) => (
          <div
            key={i}
            className="absolute pointer-events-none"
            style={{
              left: s.x,
              top: s.y,
              animationName: 'star-twinkle',
              animationDuration: `${s.dur}s`,
              animationDelay: `${s.delay}s`,
              animationTimingFunction: 'ease-in-out',
              animationIterationCount: 'infinite',
              opacity: 0,
            }}
          >
            <svg width={s.size} height={s.size} viewBox="0 0 24 24">
              <polygon
                points="12,2 14.5,9 22,9 16,14 18.5,21 12,17 5.5,21 8,14 2,9 9.5,9"
                fill="#e8941a"
              />
            </svg>
          </div>
        ))}

        {/* ── Owl ── */}
        <div
          className="absolute"
          style={{ left: '50%', top: '50%', transform: 'translate(-50%, -55%)' }}
        >
          <div className={done ? '' : 'owl-float'}>
            <svg
              width="130"
              height="148"
              viewBox="0 0 130 148"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              {/* ── Ground shadow ── */}
              <ellipse cx="65" cy="144" rx="26" ry="5" fill="rgba(0,0,0,0.07)" />

              {/* ── Body ── */}
              <ellipse cx="65" cy="96" rx="36" ry="40" fill="#1e3a5f" />

              {/* ── Chest ── */}
              <ellipse cx="65" cy="110" rx="22" ry="26" fill="#2c5282" />

              {/* ── Chest dots ── */}
              <circle cx="60" cy="102" r="2.8" fill="#1e3a5f" opacity="0.35" />
              <circle cx="70" cy="108" r="2.2" fill="#1e3a5f" opacity="0.28" />
              <circle cx="58" cy="112" r="1.8" fill="#1e3a5f" opacity="0.28" />

              {/* ── Ear tufts ── */}
              <path d="M 38 66 L 44 45 L 55 63 Z" fill="#1e3a5f" />
              <path d="M 75 63 L 86 45 L 92 66 Z" fill="#1e3a5f" />

              {/* ── Gold eye rings ── */}
              <circle cx="48" cy="75" r="17" fill="#e8941a" />
              <circle cx="82" cy="75" r="17" fill="#e8941a" />

              {/* ── Eye whites ── */}
              <circle cx="48" cy="75" r="13.5" fill="white" />
              <circle cx="82" cy="75" r="13.5" fill="white" />

              {/* ── Pupils ── */}
              <circle cx="50" cy="77" r="8" fill="#1a202c" />
              <circle cx="84" cy="77" r="8" fill="#1a202c" />

              {/* ── Eye shines ── */}
              <circle cx="55" cy="72" r="2.8" fill="white" />
              <circle cx="89" cy="72" r="2.8" fill="white" />

              {/* ── Blink eyelids (SVG animate on opacity overlay) ── */}
              {/* Left eyelid */}
              <ellipse cx="48" cy="75" rx="13.5" ry="13.5" fill="#1e3a5f">
                <animate
                  attributeName="opacity"
                  values="0;0;1;1;0;0;0;1;1;0;0"
                  keyTimes="0;0.23;0.245;0.255;0.27;0.5;0.73;0.745;0.755;0.77;1"
                  dur="7s"
                  repeatCount="indefinite"
                />
              </ellipse>

              {/* Right eyelid (slight offset → natural look) */}
              <ellipse cx="82" cy="75" rx="13.5" ry="13.5" fill="#1e3a5f">
                <animate
                  attributeName="opacity"
                  values="0;0;1;1;0;0;0;1;1;0;0"
                  keyTimes="0;0.23;0.245;0.255;0.27;0.5;0.73;0.745;0.755;0.77;1"
                  dur="7s"
                  begin="0.08s"
                  repeatCount="indefinite"
                />
              </ellipse>

              {/* ── Beak ── */}
              <path d="M 60 86 L 65 97 L 70 86 Z" fill="#e8941a" />

              {/* ── Wings ── */}
              <path d="M 29 94 Q 18 108 26 124 Q 37 111 43 99 Z" fill="#152a45" />
              <path d="M 101 94 Q 112 108 104 124 Q 93 111 87 99 Z" fill="#152a45" />

              {/* ── Feet ── */}
              <path
                d="M 50 132 L 45 141 M 50 132 L 50 141 M 50 132 L 55 141"
                stroke="#152a45" strokeWidth="2.5" strokeLinecap="round"
              />
              <path
                d="M 75 132 L 70 141 M 75 132 L 75 141 M 75 132 L 80 141"
                stroke="#152a45" strokeWidth="2.5" strokeLinecap="round"
              />

              {/* ── Done badge ── */}
              {done && (
                <>
                  <circle cx="100" cy="26" r="21" fill="#22c55e" />
                  <path
                    d="M 89 26 L 97 34 L 113 18"
                    stroke="white" strokeWidth="3.5"
                    strokeLinecap="round" strokeLinejoin="round"
                    fill="none"
                  />
                </>
              )}
            </svg>
          </div>
        </div>
      </div>

      {/* ── Message ── */}
      {!done ? (
        <>
          <p
            key={msgIdx}
            className="fade-in-up text-navy font-semibold text-base mt-1 text-center"
          >
            {WAITING_MESSAGES[msgIdx]}
          </p>

          {/* Bouncing dots */}
          <div className="flex gap-1.5 mt-3">
            {[0, 1, 2].map(i => (
              <div
                key={i}
                className="w-2 h-2 rounded-full bg-navy/40 wave-dot"
                style={{ animationDelay: `${i * 0.2}s` }}
              />
            ))}
          </div>
        </>
      ) : (
        <p className="text-green-600 font-bold text-lg mt-1 text-center fade-in-up">
          Hoàn tất! 🎉
        </p>
      )}
    </div>
  )
}

/* ---------- Main page ---------- */
export default function UploadPage() {
  const router = useRouter()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [phase, setPhase] = useState<Phase>('idle')
  const [jobId, setJobId] = useState('')
  const [errorMsg, setErrorMsg] = useState('')
  const [importType, setImportType] = useState<'text' | 'pdf2'>('text')

  const handleFileDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    const f = e.dataTransfer.files[0]
    if (f) {
      const ext = f.name.split('.').pop()?.toLowerCase()
      const allowed = importType === 'pdf2' ? ['pdf'] : ['pdf', 'docx', 'xlsx', 'tex', 'zip', 'png', 'jpg', 'jpeg']
      if (ext && allowed.includes(ext)) {
        setFile(f)
      } else {
        alert(importType === 'pdf2' ? 'Chỉ hỗ trợ file PDF đối với phương pháp Tải đề PDF 2' : 'Định dạng file không hỗ trợ')
      }
    }
  }, [importType])

  const pollStatus = useCallback(async (jid: string) => {
    const MAX_POLLS = 120 // 10 phút (5s × 120)
    let normalizingStreak = 0 // đếm số poll liên tiếp kẹt ở 'normalizing'

    for (let i = 0; i < MAX_POLLS; i++) {
      await new Promise(r => setTimeout(r, 5000))

      let data: { status?: OcrJobStatus; errorMsg?: string; state?: string }
      try {
        const res = await fetch(`/api/teacher/ocr/${jid}/status`)
        data = await res.json()
      } catch {
        // Lỗi mạng tạm thời → tiếp tục poll
        continue
      }

      const s = data.status as OcrJobStatus

      // ── OCR xong → gọi normalize ──────────────────────────────────────────
      if (s === 'ocr_done') {
        setPhase('normalizing')
        normalizingStreak = 0
        try {
          const normRes = await fetch(`/api/teacher/ocr/${jid}/normalize`, { method: 'POST' })
          const normData = await normRes.json()
          if (normData.error) {
            setPhase('error')
            setErrorMsg(normData.error)
            return
          }
        } catch {
          // Timeout hoặc lỗi mạng khi normalize → poll lại để check status DB
        }
        continue // poll tiếp để xác nhận status DB
      }

      // ── Đang normalize → chờ, hoặc retry nếu kẹt quá lâu ─────────────────
      if (s === 'normalizing') {
        setPhase('normalizing')
        normalizingStreak++
        // Nếu kẹt > 12 poll (~60s) → serverless đã bị timeout, retry normalize
        if (normalizingStreak >= 12) {
          normalizingStreak = 0
          try {
            await fetch(`/api/teacher/ocr/${jid}/normalize`, { method: 'POST' })
          } catch { /* tiếp tục poll */ }
        }
        continue
      }

      // ── Đang extracting → chờ server hoàn thành ───────────────────────────
      if (s === 'extracting') {
        setPhase('extracting')
        normalizingStreak = 0
        continue
      }

      // ── Normalize xong → chờ user vào edit page ───────────────────────────
      if (s === 'normalized') {
        setPhase('normalized')
        return
      }

      // ── Pipeline hoàn toàn xong (extract đã chạy) ─────────────────────────
      if (s === 'done') {
        setPhase('done')
        return
      }

      // ── Lỗi từ server ─────────────────────────────────────────────────────
      if (s === 'error') {
        setPhase('error')
        setErrorMsg(data.errorMsg || 'Lỗi không xác định')
        return
      }

      // ocr_running / uploading / pending → tiếp tục poll
      normalizingStreak = 0
    }
    setPhase('error')
    setErrorMsg('Hết thời gian chờ (10 phút). Vui lòng thử lại.')
  }, [])

  const handleUpload = async () => {
    if (!file) return
    setPhase('uploading')
    setErrorMsg('')

    const form = new FormData()
    form.append('pdf', file)
    form.append('import_type', importType)

    const res = await fetch('/api/teacher/ocr/upload', { method: 'POST', body: form })
    const data = await res.json()

    if (data.error) {
      setPhase('error')
      setErrorMsg(data.error)
      return
    }

    setJobId(data.jobId)
    setPhase('polling')
    pollStatus(data.jobId)
  }

  const isDone = phase === 'normalized' || phase === 'done'

  return (
    <div className="p-10 max-w-3xl">
      <div className="text-xs tracking-label text-ink-50 font-mono">(01) Tải đề</div>
      <h1 className="font-display text-5xl sm:text-6xl text-ink mt-6 leading-tight">
        Tạo đề <em className="italic">mới</em>.
      </h1>
      <p className="mt-6 text-base text-ink-70 leading-relaxed max-w-2xl">
        Chọn File hoặc kéo thả File vào đây. Hỗ trợ các định dạng .pdf, .docx, .xlsx, .tex, .zip, Ảnh.
      </p>

      {/* Phương thức import */}
      {phase === 'idle' && (
        <div className="mt-8 flex gap-4 border-b border-line pb-6">
          <button
            type="button"
            onClick={() => {
              setImportType('text')
              setFile(null)
            }}
            className={`px-5 py-2.5 text-sm font-medium border transition-all ${
              importType === 'text'
                ? 'bg-ink text-paper border-ink'
                : 'bg-transparent text-ink-50 border-line hover:border-ink hover:text-ink'
            }`}
          >
            Số hóa Text & Công thức (OCR)
          </button>
          <button
            type="button"
            onClick={() => {
              setImportType('pdf2')
              setFile(null)
            }}
            className={`px-5 py-2.5 text-sm font-medium border transition-all ${
              importType === 'pdf2'
                ? 'bg-ink text-paper border-ink'
                : 'bg-transparent text-ink-50 border-line hover:border-ink hover:text-ink'
            }`}
          >
            Tải đề PDF 2 (Cắt câu dạng ảnh)
          </button>
        </div>
      )}

      <div className="mt-12">
        {/* Upload zone */}
        {phase === 'idle' && (
          <div
            onDrop={handleFileDrop}
            onDragOver={e => e.preventDefault()}
            onClick={() => fileInputRef.current?.click()}
            className="border border-dashed border-line p-16 text-center cursor-pointer hover:border-ink hover:bg-paper-soft transition-colors"
          >
            <input
              ref={fileInputRef}
              type="file"
              accept={importType === 'pdf2' ? '.pdf' : '.pdf,.docx,.xlsx,.tex,.zip,.png,.jpg,.jpeg'}
              className="hidden"
              onChange={e => {
                const f = e.target.files?.[0] ?? null
                if (f) {
                  const ext = f.name.split('.').pop()?.toLowerCase()
                  const allowed = importType === 'pdf2' ? ['pdf'] : ['pdf', 'docx', 'xlsx', 'tex', 'zip', 'png', 'jpg', 'jpeg']
                  if (ext && allowed.includes(ext)) {
                    setFile(f)
                  } else {
                    alert('Chỉ hỗ trợ file PDF đối với phương pháp Tải đề PDF 2')
                  }
                }
              }}
            />
            <Upload size={32} className="text-ink-30 mx-auto mb-4" />
            <p className="font-display text-2xl text-ink italic">Chọn File hoặc kéo thả File vào đây</p>
            <p className="text-xs tracking-label text-ink-50 mt-3">
              {importType === 'pdf2'
                ? 'Chỉ hỗ trợ PDF (Tối đa 50MB) - Phân đoạn tự động dạng ảnh chuẩn xác 100%'
                : 'Hỗ trợ PDF, Word, Excel, Latex, Zip, Ảnh (Tối đa 50MB)'}
            </p>
          </div>
        )}

        {/* File selected bar */}
        {phase === 'idle' && file && (
          <div className="mt-8 flex items-center justify-between gap-4 border-t border-b border-line py-5">
            <div className="flex items-center gap-3 min-w-0">
              <FileText size={18} className="text-ink-50 shrink-0" />
              <div className="min-w-0">
                <p className="font-display text-xl text-ink truncate">{file.name}</p>
                <p className="text-xs tracking-label text-ink-50">{(file.size / 1024 / 1024).toFixed(1)} MB</p>
              </div>
            </div>
            <button
              onClick={handleUpload}
              className="inline-flex items-center gap-2 px-6 py-3 bg-ink text-paper text-sm tracking-label hover:bg-moss transition-colors shrink-0"
            >
              Bắt đầu xử lý <span aria-hidden>→</span>
            </button>
          </div>
        )}

        {/* Waiting / Done */}
        {phase !== 'idle' && phase !== 'error' && (
          <div className="bg-paper-soft py-8">
            <OwlWaiting done={isDone} />

            {isDone && (
              <div className="px-6 pb-8 flex flex-col items-center gap-6 mt-4">
                <p className="text-base text-ink-70 text-center max-w-md">
                  Câu hỏi đã được trích xuất và chuẩn hóa.
                  Hãy kiểm tra lại trước khi đăng bài.
                </p>
                <button
                  onClick={() => router.push(`/teacher/ocr/${jobId}/edit`)}
                  className="inline-flex items-center gap-2 px-7 py-3.5 bg-ink text-paper text-sm tracking-label hover:bg-moss"
                >
                  Mở trình chỉnh sửa <span aria-hidden>→</span>
                </button>
              </div>
            )}
          </div>
        )}

        {/* Error */}
        {phase === 'error' && (
          <div className="border-l-2 border-ember pl-6 py-4">
            <div className="flex items-start gap-3">
              <AlertCircle size={18} className="text-ember shrink-0 mt-1" />
              <div>
                <p className="text-xs tracking-label text-ember">Đã xảy ra lỗi</p>
                <p className="font-display text-2xl text-ink mt-2">{errorMsg}</p>
              </div>
            </div>
            <div className="flex gap-6 mt-6">
              {jobId && (
                <button
                  onClick={() => { setPhase('polling'); pollStatus(jobId) }}
                  className="text-sm tracking-label text-ink link-editorial"
                >
                  Thử lại →
                </button>
              )}
              <button
                onClick={() => { setPhase('idle'); setFile(null); setJobId(''); setErrorMsg('') }}
                className="text-sm tracking-label text-ink-50 link-editorial"
              >
                Bắt đầu lại
              </button>
            </div>
          </div>
        )}

        {/* Tips */}
        {phase === 'idle' && (
          <div className="mt-12 border-l-2 border-moss pl-6">
            <p className="text-xs tracking-label text-moss mb-3">Lưu ý</p>
            <ul className="space-y-2 text-base text-ink-70">
              <li>— PDF đề thi các môn THPT, có thể bản scan hoặc bản text</li>
              <li>— Thời gian xử lý: 2-5 phút tùy độ dài đề</li>
              <li>— Sau khi trích xuất, bạn có thể chỉnh sửa từng câu trước khi đăng</li>
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}
