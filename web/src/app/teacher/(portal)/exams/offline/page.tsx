'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Save, Upload, Plus, Trash2, CheckCircle, FileSpreadsheet } from 'lucide-react'
import { createClient } from '@/lib/supabase'

interface CodeAns {
  code: string // e.g. "101"
  answers: Record<number, string> // e.g. { 1: "A", 2: "B" }
}

const SUBJECT_OPTIONS = [
  { id: 1, name: 'Toán' },
  { id: 2, name: 'Vật Lý' },
  { id: 3, name: 'Hóa Học' },
  { id: 4, name: 'Sinh Học' },
  { id: 6, name: 'Lịch Sử' },
  { id: 7, name: 'Địa Lý' },
  { id: 8, name: 'GDCD' },
  { id: 9, name: 'Tiếng Anh' },
]

export default function OfflineExamPage() {
  const router = useRouter()
  const supabase = createClient()

  // Form states
  const [title, setTitle] = useState('')
  const [subjectId, setSubjectId] = useState(1)
  const [year, setYear] = useState(new Date().getFullYear())
  const [questionCount, setQuestionCount] = useState(20)
  
  // Multiple codes (Mã đề) state
  const [codes, setCodes] = useState<CodeAns[]>([
    { code: '101', answers: {} },
    { code: '102', answers: {} },
  ])

  const [saving, setSaving] = useState(false)
  const [excelFile, setExcelFile] = useState<File | null>(null)
  const [importing, setImporting] = useState(false)
  const [successMsg, setSuccessMsg] = useState('')
  const [errorMsg, setErrorMsg] = useState('')

  // Adjust answers when question count changes
  useEffect(() => {
    setCodes(prev =>
      prev.map(c => {
        const cleaned: Record<number, string> = {}
        for (let i = 1; i <= questionCount; i++) {
          cleaned[i] = c.answers[i] ?? ''
        }
        return { ...c, answers: cleaned }
      })
    )
  }, [questionCount])

  // Handle cell click (select answer A/B/C/D)
  const handleAnswerSelect = (codeIndex: number, qNum: number, ans: string) => {
    setCodes(prev => {
      const copy = [...prev]
      const current = copy[codeIndex]
      current.answers[qNum] = current.answers[qNum] === ans ? '' : ans // toggle
      return copy
    })
  }

  // Add new code (mã đề)
  const addCode = () => {
    const nextCode = String(101 + codes.length)
    setCodes(prev => [...prev, { code: nextCode, answers: {} }])
  }

  // Remove code
  const removeCode = (index: number) => {
    if (codes.length <= 1) return
    setCodes(prev => prev.filter((_, i) => i !== index))
  }

  // Update code text (e.g. rename "101" to "204")
  const updateCodeName = (index: number, name: string) => {
    setCodes(prev => {
      const copy = [...prev]
      copy[index].code = name
      return copy
    })
  }

  // Handle Excel upload parsing
  const handleExcelUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setExcelFile(file)
    setImporting(true)
    setErrorMsg('')

    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await fetch('/api/teacher/ocr/upload', {
        method: 'POST',
        body: formData,
      })
      const data = await res.json()
      if (data.error) {
        setErrorMsg(data.error)
        setImporting(false)
        return
      }

      // Check job status until excel parse result is done
      const interval = setInterval(async () => {
        const statusRes = await fetch(`/api/teacher/ocr/${data.jobId}/status`)
        const statusData = await statusRes.json()

        if (statusData.status === 'done') {
          clearInterval(interval)
          // Fetch draft exam questions that were parsed
          const questionsRes = await fetch(`/api/teacher/drafts/${data.jobId}/questions`)
          // Wait, we can fetch draft questions directly if we query drafts/questions
          // Let's call supabase client to query them cleanly
          const { data: draftQuestions } = await supabase
            .from('draft_questions')
            .select('correct_answer, question_number, content')
            .eq('draft_exam_id', (await supabase.from('draft_exams').select('id').eq('ocr_job_id', data.jobId).single()).data?.id)

          if (draftQuestions) {
            // Group answers by mã đề.
            // Excel format outputs keys: we can parse correctly.
            // For simplicity, let's map whatever answers we got into the codes state.
            const parsedCodesMap: Record<string, Record<number, string>> = {}
            let maxQ = 0
            
            // Re-group parsed excel rows
            draftQuestions.forEach((q: any) => {
              // content usually has "Đáp án mã đề 101"
              const codeMatch = q.content.match(/mã đề\s*(\d+)/i)
              const code = codeMatch ? codeMatch[1] : '101'
              const num = q.question_number
              if (num > maxQ) maxQ = num
              if (!parsedCodesMap[code]) parsedCodesMap[code] = {}
              parsedCodesMap[code][num] = q.correct_answer || ''
            })

            const newCodes = Object.entries(parsedCodesMap).map(([code, answers]) => ({
              code,
              answers
            }))

            if (newCodes.length > 0) {
              setCodes(newCodes)
              if (maxQ > 0) setQuestionCount(maxQ)
              setSuccessMsg('✓ Đã import đáp án từ Excel thành công!')
              setTimeout(() => setSuccessMsg(''), 4000)
            }
          }
          setImporting(false)
        } else if (statusData.status === 'error') {
          clearInterval(interval)
          setErrorMsg(statusData.errorMsg || 'Lỗi parse Excel')
          setImporting(false)
        }
      }, 2000)
    } catch (err) {
      setErrorMsg('Lỗi kết nối máy chủ')
      setImporting(false)
    }
  }

  // Submit and save Offline exam keys
  const handleSubmit = async () => {
    if (!title.trim()) {
      setErrorMsg('Vui lòng nhập tên đề thi')
      return
    }

    setSaving(true)
    setErrorMsg('')

    try {
      const res = await fetch('/api/teacher/exams/offline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title,
          subject_id: subjectId,
          year,
          question_count: questionCount,
          codes
        })
      })

      const data = await res.json()
      if (data.error) {
        setErrorMsg(data.error)
      } else {
        setSuccessMsg('✓ Lưu bảng đáp án đề thi offline thành công!')
        setTimeout(() => {
          router.push('/teacher/dashboard')
        }, 1500)
      }
    } catch {
      setErrorMsg('Lỗi lưu dữ liệu')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {/* Back button */}
      <div className="flex items-center gap-3 mb-6">
        <Link href="/teacher/dashboard" className="text-ink-50 hover:text-ink transition-colors">
          <ArrowLeft size={20} />
        </Link>
        <div>
          <p className="text-xs tracking-label text-ink-50 font-mono">(Offline Mode)</p>
          <h1 className="font-display text-4xl text-ink leading-tight">
            Tạo đề <em className="italic">Offline</em> thủ công.
          </h1>
        </div>
      </div>

      {/* Grid Settings Card */}
      <div className="bg-paper-soft border border-line p-6 mb-8 grid grid-cols-1 md:grid-cols-4 gap-5">
        <div className="md:col-span-2">
          <label className="block text-xs tracking-label text-ink-50 uppercase mb-2">Tên đề thi / Bài tập</label>
          <input
            type="text"
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="Ví dụ: Đề thi offline giữa kì I Toán 10"
            className="w-full bg-paper border border-line px-3 py-2 text-sm focus:outline-none focus:border-ink"
          />
        </div>
        <div>
          <label className="block text-xs tracking-label text-ink-50 uppercase mb-2">Môn học</label>
          <select
            value={subjectId}
            onChange={e => setSubjectId(Number(e.target.value))}
            className="w-full bg-paper border border-line px-3 py-2 text-sm focus:outline-none focus:border-ink"
          >
            {SUBJECT_OPTIONS.map(s => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs tracking-label text-ink-50 uppercase mb-2">Số câu hỏi</label>
          <input
            type="number"
            min={1}
            max={100}
            value={questionCount}
            onChange={e => setQuestionCount(Number(e.target.value))}
            className="w-full bg-paper border border-line px-3 py-2 text-sm focus:outline-none focus:border-ink"
          />
        </div>
      </div>

      {/* Excel quick import */}
      <div className="border border-dashed border-line p-6 mb-8 text-center rounded-xl bg-paper-soft/40">
        <div className="flex flex-col items-center gap-3">
          <div className="flex items-center gap-2">
            <FileSpreadsheet size={20} className="text-moss" />
            <span className="font-semibold text-ink-70 text-sm">Nhập nhanh từ Excel bảng đáp án đối thủ Azota</span>
          </div>
          <p className="text-xs text-ink-40">
            Hỗ trợ import trực tiếp file Excel đáp án offline mẫu của Azota để tự động điền các phương án đúng.
          </p>
          <label className="inline-flex items-center gap-2 px-4 py-2 bg-ink text-paper text-xs tracking-label hover:bg-moss transition-colors cursor-pointer mt-2">
            <Upload size={14} />
            {importing ? 'Đang phân tích Excel…' : 'Chọn file Excel đáp án'}
            <input
              type="file"
              accept=".xlsx"
              onChange={handleExcelUpload}
              disabled={importing}
              className="hidden"
            />
          </label>
        </div>
      </div>

      {/* Notifications */}
      {errorMsg && (
        <div className="mb-6 p-4 bg-ember-soft border border-ember/20 text-ember text-sm rounded-lg">
          ✕ {errorMsg}
        </div>
      )}
      {successMsg && (
        <div className="mb-6 p-4 bg-green-50 border border-green-200 text-green-700 text-sm rounded-lg flex items-center gap-2">
          <CheckCircle size={16} /> {successMsg}
        </div>
      )}

      {/* Codes header / editor */}
      <div className="mb-6 flex justify-between items-center">
        <h3 className="font-semibold text-ink-70 text-base">Danh sách mã đề và đáp án tương ứng</h3>
        <button
          onClick={addCode}
          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 border border-line text-ink-70 text-xs font-semibold hover:bg-paper-soft transition-colors"
        >
          <Plus size={14} /> Thêm mã đề
        </button>
      </div>

      {/* Interactive Answer Grid Table */}
      <div className="bg-paper border border-line overflow-x-auto mb-8">
        <table className="border-collapse w-full min-w-max text-left text-sm">
          <thead>
            <tr className="bg-paper-soft border-b border-line text-xs tracking-label text-ink-50 uppercase">
              <th className="p-4 w-20 text-center">Câu</th>
              {codes.map((c, ci) => (
                <th key={ci} className="p-4 text-center border-l border-line min-w-64">
                  <div className="flex items-center justify-center gap-2">
                    <span className="font-mono text-ink-70">Mã đề:</span>
                    <input
                      type="text"
                      value={c.code}
                      onChange={e => updateCodeName(ci, e.target.value)}
                      className="w-16 bg-paper border border-line px-2 py-1 text-center text-xs font-bold font-mono focus:outline-none"
                    />
                    {codes.length > 1 && (
                      <button
                        onClick={() => removeCode(ci)}
                        className="text-ink-30 hover:text-ember transition-colors"
                        title="Xóa mã đề này"
                      >
                        <Trash2 size={13} />
                      </button>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: questionCount }).map((_, qi) => {
              const qNum = qi + 1
              return (
                <tr key={qNum} className="border-b border-line hover:bg-paper-soft/40 transition-colors">
                  <td className="p-3 text-center font-mono font-bold text-ink-50 bg-paper-soft/20">{qNum}</td>
                  {codes.map((c, ci) => {
                    const selectedAns = c.answers[qNum] || ''
                    return (
                      <td key={ci} className="p-3 border-l border-line text-center">
                        <div className="flex items-center justify-center gap-2">
                          {['A', 'B', 'C', 'D'].map(option => {
                            const isSelected = selectedAns === option
                            return (
                              <button
                                key={option}
                                onClick={() => handleAnswerSelect(ci, qNum, option)}
                                className={`w-8 h-8 rounded-full border text-xs font-mono font-bold transition-all duration-150 ${
                                  isSelected
                                    ? 'bg-ink text-paper border-ink scale-105 shadow-sm'
                                    : 'border-line text-ink-50 hover:border-ink hover:text-ink bg-transparent'
                                }`}
                              >
                                {option}
                              </button>
                            )
                          })}
                        </div>
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Save Action */}
      <div className="flex justify-end gap-4 border-t border-line pt-6">
        <Link href="/teacher/dashboard" className="px-6 py-3 border border-line text-ink-50 text-sm tracking-label hover:bg-paper-soft transition-colors">
          Hủy bỏ
        </Link>
        <button
          onClick={handleSubmit}
          disabled={saving || !title.trim()}
          className="inline-flex items-center gap-2 px-8 py-3 bg-ink text-paper text-sm tracking-label font-bold hover:bg-moss disabled:opacity-50 transition-colors cursor-pointer"
        >
          {saving ? 'Đang lưu…' : 'Lưu bảng đáp án đề Offline →'}
        </button>
      </div>
    </div>
  )
}
