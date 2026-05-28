'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { Save, ChevronRight, Loader2, AlertCircle } from 'lucide-react'

type SaveStatus = 'saved' | 'saving' | 'unsaved'

export default function EditorPage() {
  const params = useParams<{ jobId: string }>()
  const router = useRouter()

  const [markdown, setMarkdown] = useState('')
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [filename, setFilename] = useState('')
  const [loading, setLoading] = useState(true)
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('saved')
  const [extracting, setExtracting] = useState(false)
  const [extractError, setExtractError] = useState('')

  const saveTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

  useEffect(() => {
    fetch(`/api/teacher/ocr/${params.jobId}/markdown`)
      .then(r => r.json())
      .then(data => {
        if (data.draftExamId && data.filename?.toLowerCase().endsWith('.xlsx')) {
          router.push(`/teacher/drafts/${data.draftExamId}`)
          return
        }
        setMarkdown(data.markdown ?? '')
        setPdfUrl(data.pdfUrl ?? null)
        setFilename(data.filename ?? '')
        setLoading(false)
      })
  }, [params.jobId, router])

  const save = useCallback(async (value: string) => {
    setSaveStatus('saving')
    await fetch(`/api/teacher/ocr/${params.jobId}/markdown`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ markdown: value }),
    })
    setSaveStatus('saved')
  }, [params.jobId])

  const handleChange = useCallback((value: string) => {
    setMarkdown(value)
    setSaveStatus('unsaved')
    clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(() => save(value), 1500)
  }, [save])

  const handleExtract = async () => {
    setExtracting(true)
    setExtractError('')
    // Lưu trước khi tạo câu hỏi
    clearTimeout(saveTimer.current)
    await save(markdown)

    const res = await fetch(`/api/teacher/ocr/${params.jobId}/extract`, { method: 'POST' })
    const data = await res.json()
    if (data.error) {
      setExtractError(data.error)
      setExtracting(false)
      return
    }
    router.push(`/teacher/drafts/${data.draftExamId}`)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center" style={{ height: '100vh' }}>
        <Loader2 size={28} className="text-navy animate-spin" />
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      {/* Topbar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12,
        padding: '0 16px', height: 48, flexShrink: 0,
        background: 'white', borderBottom: '1px solid #e5e7eb',
      }}>
        <span style={{ fontWeight: 700, fontSize: 14, color: '#1e3a5f', maxWidth: 320, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {filename}
        </span>
        <span style={{ flex: 1 }} />
        <span style={{ fontSize: 12, display: 'flex', alignItems: 'center', gap: 4,
          color: saveStatus === 'saved' ? '#059669' : saveStatus === 'saving' ? '#d97706' : '#9ca3af' }}>
          {saveStatus === 'saving'
            ? <><Loader2 size={12} className="animate-spin" /> Đang lưu...</>
            : saveStatus === 'saved'
            ? <><Save size={12} /> Đã lưu</>
            : '● Chưa lưu'}
        </span>
        <div style={{ width: 1, height: 20, background: '#e5e7eb', margin: '0 4px' }} />
        {extractError && (
          <span style={{ fontSize: 12, color: '#dc2626', display: 'flex', alignItems: 'center', gap: 4 }}>
            <AlertCircle size={12} /> {extractError}
          </span>
        )}
        <button
          onClick={handleExtract}
          disabled={extracting}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '6px 14px', borderRadius: 8, border: 'none', cursor: extracting ? 'not-allowed' : 'pointer',
            background: extracting ? '#9ca3af' : '#1e3a5f', color: 'white',
            fontSize: 13, fontWeight: 600,
          }}
        >
          {extracting
            ? <><Loader2 size={14} className="animate-spin" /> Đang tạo câu hỏi...</>
            : <>Tạo câu hỏi <ChevronRight size={14} /></>}
        </button>
      </div>

      {/* Split view */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* PDF panel */}
        <div style={{ width: '45%', borderRight: '1px solid #e5e7eb', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ padding: '6px 12px', background: '#f9fafb', borderBottom: '1px solid #e5e7eb', fontSize: 11, fontWeight: 600, color: '#6b7280', letterSpacing: '0.05em' }}>
            PDF GỐC
          </div>
          {pdfUrl ? (
            <embed src={pdfUrl} type="application/pdf" width="100%" style={{ flex: 1, display: 'block', height: '100%' }} />
          ) : (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 8, color: '#9ca3af' }}>
              <AlertCircle size={32} />
              <span style={{ fontSize: 13 }}>PDF không có sẵn</span>
              <span style={{ fontSize: 11 }}>Bạn vẫn có thể chỉnh sửa markdown bên phải</span>
            </div>
          )}
        </div>

        {/* Markdown panel */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ padding: '6px 12px', background: '#f9fafb', borderBottom: '1px solid #e5e7eb', fontSize: 11, fontWeight: 600, color: '#6b7280', letterSpacing: '0.05em' }}>
            MARKDOWN CHUẨN HÓA (EXAM-TAG-12) — chỉnh sửa tùy ý trước khi tạo câu hỏi
          </div>
          <textarea
            value={markdown}
            onChange={e => handleChange(e.target.value)}
            spellCheck={false}
            style={{
              flex: 1, resize: 'none', border: 'none', outline: 'none',
              fontFamily: '"Cascadia Code", "Fira Code", "JetBrains Mono", Consolas, monospace',
              fontSize: 13, lineHeight: 1.6, padding: '12px 16px',
              background: 'white', color: '#1f2937',
            }}
          />
        </div>
      </div>
    </div>
  )
}
