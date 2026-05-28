'use client'

import katex from 'katex'
import type { Question } from '@/lib/types'
import { CheckCircle, XCircle, AlertCircle } from 'lucide-react'
import ReportButton from './ReportButton'

interface QuestionCardProps {
  question: Question
  index: number
  selectedAnswer?: string
  onAnswer: (questionId: number, answer: string) => void
  showResult?: boolean
  isPaperLayout?: boolean
}

export function renderLatex(text: string): string {
  // ─── BUG FIX (sqrt invisible) ───
  // The old approach ran `replace(/\n/g, '<br/>')` on the FINAL HTML, which
  // also replaced `\n` characters inside KaTeX-generated SVG <path d="...">
  // attribute values — corrupting the path data and making radical signs
  // invisible. Strategy now:
  //   1. Tokenise the input by math delimiters $...$ and $$...$$
  //   2. Render KaTeX only on math tokens — its HTML output is left untouched
  //   3. Apply markdown/newline replacements only on the text tokens
  //   4. Re-join
  const MATH_RE = /(\$\$[\s\S]+?\$\$|\$(?:[^$\\\n]|\\.)+?\$)/g

  const segments = text.split(MATH_RE)

  const result = segments.map(seg => {
    // Math segment → render via KaTeX, do NOT post-process
    if (seg.startsWith('$$') && seg.endsWith('$$')) {
      const math = seg.slice(2, -2).trim()
      try {
        const html = katex.renderToString(math, { displayMode: true, throwOnError: false })
        return html.replace(/\r?\n/g, ' ')
      }
      catch { return seg }
    }
    if (seg.startsWith('$') && seg.endsWith('$') && seg.length > 1) {
      const math = seg.slice(1, -1).trim()
      try {
        const html = katex.renderToString(math, { displayMode: false, throwOnError: false })
        return html.replace(/\r?\n/g, ' ')
      }
      catch { return seg }
    }

    // Plain text segment → apply ALL text transformations here
    // (NOT on the final joined string — that would corrupt KaTeX SVG paths)
    let s = seg

    // Markdown images
    s = s.replace(
      /!\[([^\]]*)\]\(([^)]+)\)/g,
      '<img src="$2" alt="$1" style="max-width:100%;margin:0.75rem 0;border-radius:0.5rem" />'
    )

    // Style existing HTML tables (from OCR pipeline)
    s = s.replace(/<table>/gi,
      '<table style="border-collapse:collapse;margin:0.5rem auto;font-size:0.875rem;display:table">'
    )
    s = s.replace(/<td(\s[^>]*)?>/gi,
      (_, attrs = '') => `<td${attrs} style="border:1px solid #9ca3af;padding:0.25rem 0.6rem;text-align:center;white-space:nowrap">`
    )
    s = s.replace(/<th(\s[^>]*)?>/gi,
      (_, attrs = '') => `<th${attrs} style="border:1px solid #9ca3af;padding:0.25rem 0.6rem;text-align:center;font-weight:600;background:#f3f4f6;white-space:nowrap">`
    )

    // Markdown tables (uses \n to detect rows — MUST run BEFORE newline → <br/>)
    s = s.replace(/(\|[^\n]+(?:\n\|[^\n]+)+)/g, (tableBlock) => {
      const rows = tableBlock.trim().split('\n').filter(r => r.trim())
      if (rows.length < 2) return tableBlock
      const isSep = (row: string) => row.split('|').slice(1, -1).every(c => /^\s*[-:]+\s*$/.test(c))
      const hasHeader = rows.length >= 2 && isSep(rows[1])
      let html = '<table style="border-collapse:collapse;margin:0.5rem auto;font-size:0.875rem;display:table">'
      let rowIdx = 0
      for (const row of rows) {
        if (isSep(row)) continue
        const cells = row.split('|').slice(1, -1)
        const tag = hasHeader && rowIdx === 0 ? 'th' : 'td'
        const bg = hasHeader && rowIdx === 0 ? 'background:#f3f4f6;font-weight:600;' : ''
        html += '<tr>'
        for (const cell of cells)
          html += `<${tag} style="border:1px solid #9ca3af;padding:0.25rem 0.6rem;text-align:center;white-space:nowrap;${bg}">${cell.trim()}</${tag}>`
        html += '</tr>'
        rowIdx++
      }
      return html + '</table>'
    })

    // Newlines → <br/> (SAFE here — KaTeX SVG paths are in a different segment)
    s = s.replace(/\n/g, '<br/>')
    return s
  }).join('')

  return result
}

export function renderContent(text: string): React.ReactNode {
  return <span dangerouslySetInnerHTML={{ __html: renderLatex(text) }} />
}

// Strip option lines [A]./[a]. from question content when options are shown separately
export function getDisplayContent(question: Question): string {
  if (!question.options) return question.content
  // Find first [A]/[a] marker and slice everything before it
  const idx = question.content.search(/\n\s*\[[aAbBcCdD]\]/)
  return idx >= 0 ? question.content.slice(0, idx).trim() : question.content
}

const OPTION_LABELS = ['A', 'B', 'C', 'D']
export const LEVEL_COLORS: Record<string, string> = {
  'Nhận biết': 'bg-emerald-100 text-emerald-700',
  'Thông hiểu': 'bg-blue-100 text-blue-700',
  'Vận dụng': 'bg-orange-100 text-orange-700',
  'Vận dụng cao': 'bg-red-100 text-red-700',
}

export default function QuestionCard({
  question,
  index,
  selectedAnswer,
  onAnswer,
  showResult = false,
  isPaperLayout = false,
}: QuestionCardProps) {
  const isCorrect = showResult && !!question.correct_answer && selectedAnswer === question.correct_answer
  const isWrong = showResult && !!question.correct_answer && selectedAnswer !== question.correct_answer

  return (
    <div className={`bg-white rounded-2xl p-6 card-shadow border ${
      showResult
        ? isCorrect ? 'border-emerald-200' : isWrong ? 'border-red-200' : 'border-gray-200'
        : 'border-gray-100'
    }`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-4">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="bg-navy text-white text-xs font-bold px-2.5 py-1 rounded-full">
            Câu {index + 1}
          </span>
          {question.level && (
            <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${LEVEL_COLORS[question.level] || 'bg-gray-100 text-gray-600'}`}>
              {question.level}
            </span>
          )}
          <span className="text-xs text-gray-400 bg-gray-50 px-2.5 py-1 rounded-full">
            {question.question_type === 'trac_nghiem' ? 'Trắc nghiệm' :
             question.question_type === 'dung_sai' ? 'Đúng/Sai' : 'Tự luận'}
          </span>
        </div>
        <div className="shrink-0 flex items-center gap-4">
          <ReportButton questionId={question.id} />
          {showResult && (
            isCorrect
              ? <CheckCircle size={22} className="text-emerald-500" />
              : isWrong
              ? <XCircle size={22} className="text-red-500" />
              : <AlertCircle size={22} className="text-gray-400" />
          )}
        </div>
      </div>

      {/* Question content — strip option lines when options are rendered below */}
      <div className="text-gray-800 text-base leading-relaxed mb-5 font-medium">
        {renderContent(getDisplayContent(question))}
      </div>

      {/* ── Trắc nghiệm ── */}
      {question.question_type === 'trac_nghiem' && !question.options && (
        <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-sm text-amber-700">
          ⚠️ Câu hỏi này chưa có đáp án cấu trúc. Xem nội dung câu hỏi bên trên.
        </div>
      )}
      {question.question_type === 'trac_nghiem' && question.options && (
        isPaperLayout ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-3 mt-3 pl-2">
            {OPTION_LABELS.map(key => {
              const optText = question.options?.[key]
              if (!optText) return null
              const isSelected = selectedAnswer === key
              const isCorrectOpt = showResult && question.correct_answer === key
              const isWrongOpt = showResult && isSelected && !isCorrectOpt
              return (
                <div
                  key={key}
                  onClick={() => !showResult && onAnswer(question.id, key)}
                  className={`flex items-start gap-2.5 py-1.5 px-3 rounded-lg cursor-pointer transition-all duration-200 group text-sm select-none ${
                    isCorrectOpt
                      ? 'bg-emerald-50 text-emerald-800 font-medium'
                      : isWrongOpt
                      ? 'bg-red-50 text-red-800 font-medium'
                      : isSelected
                      ? 'bg-navy-50 text-navy font-semibold'
                      : 'hover:bg-gray-50 text-gray-700'
                  }`}
                >
                  <span
                    className={`inline-flex items-center justify-center w-6 h-6 rounded-full border text-xs font-bold transition-all shrink-0 mt-0.5 ${
                      isCorrectOpt
                        ? 'bg-emerald-500 border-emerald-500 text-white'
                        : isWrongOpt
                        ? 'bg-red-500 border-red-500 text-white'
                        : isSelected
                        ? 'bg-navy border-navy text-white'
                        : 'border-gray-300 text-gray-400 group-hover:border-navy group-hover:text-navy'
                    }`}
                  >
                    {key}
                  </span>
                  <span className="leading-relaxed pt-0.5">{renderContent(optText)}</span>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-2">
            {OPTION_LABELS.map(key => {
              const optText = question.options?.[key]
              if (!optText) return null
              const isSelected = selectedAnswer === key
              const isCorrectOpt = showResult && question.correct_answer === key
              const isWrongOpt = showResult && isSelected && !isCorrectOpt
              return (
                <button
                  key={key}
                  onClick={() => !showResult && onAnswer(question.id, key)}
                  disabled={showResult}
                  className={`flex items-start gap-3 px-4 py-3 rounded-xl border-2 text-left transition-all text-sm ${
                    isCorrectOpt ? 'border-emerald-400 bg-emerald-50 text-emerald-800'
                    : isWrongOpt ? 'border-red-400 bg-red-50 text-red-800'
                    : isSelected ? 'border-navy bg-navy-50 text-navy font-medium'
                    : 'border-gray-200 bg-white hover:border-navy-100 hover:bg-navy-50 text-gray-700'
                  }`}
                >
                  <span className={`shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold mt-0.5 ${
                    isCorrectOpt ? 'bg-emerald-500 text-white'
                    : isWrongOpt ? 'bg-red-500 text-white'
                    : isSelected ? 'bg-navy text-white'
                    : 'bg-gray-100 text-gray-600'
                  }`}>{key}</span>
                  <span className="leading-relaxed">{renderContent(optText)}</span>
                </button>
              )
            })}
          </div>
        )
      )}

      {/* ── Đúng/Sai — 4 sub-statements ── */}
      {question.question_type === 'dung_sai' && (
        <div className="space-y-2">
          {question.options
            ? OPTION_LABELS.map((key, idx) => {
                const subText = question.options?.[key]
                if (!subText) return null

                // correct_answer = "DSDS" (D=Đúng S=Sai), selectedAnswer same format
                const myChar = (selectedAnswer && idx < selectedAnswer.length)
                  ? selectedAnswer[idx].toUpperCase() : undefined
                const correctChar = (question.correct_answer && idx < question.correct_answer.length)
                  ? question.correct_answer[idx].toUpperCase() : undefined

                const isSubCorrect = showResult && !!correctChar && myChar === correctChar
                const isSubWrong   = showResult && !!correctChar && myChar !== correctChar

                return (
                  <div
                    key={key}
                    className={`rounded-xl border-2 p-3 transition-all ${
                      isSubCorrect ? 'border-emerald-300 bg-emerald-50'
                      : isSubWrong ? 'border-red-200 bg-red-50'
                      : 'border-gray-100 bg-gray-50'
                    }`}
                  >
                    <div className="flex items-start gap-2 mb-2">
                      <span className={`shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold mt-0.5 ${
                        isSubCorrect ? 'bg-emerald-500 text-white'
                        : isSubWrong ? 'bg-red-400 text-white'
                        : 'bg-gray-200 text-gray-600'
                      }`}>{key}</span>
                      <div className="flex-1 text-sm leading-relaxed text-gray-800">
                        {renderContent(subText)}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 ml-8">
                      {([{ val: 'D', label: 'Đúng' }, { val: 'S', label: 'Sai' }] as const).map(({ val, label }) => {
                        const isSel        = myChar === val
                        const isCorrectBtn = showResult && correctChar === val
                        const isWrongBtn   = showResult && isSel && correctChar !== val
                        return (
                          <button
                            key={val}
                            onClick={() => {
                              if (showResult) return
                              const base = (selectedAnswer || '').padEnd(4, '?').split('')
                              base[idx] = val
                              onAnswer(question.id, base.join(''))
                            }}
                            disabled={showResult}
                            className={`px-3 py-1 rounded-lg border-2 font-semibold text-xs transition-all ${
                              isCorrectBtn ? 'border-emerald-400 bg-emerald-500 text-white'
                              : isWrongBtn ? 'border-red-400 bg-red-500 text-white'
                              : isSel ? 'border-navy bg-navy text-white'
                              : 'border-gray-200 text-gray-500 hover:border-navy hover:bg-navy-50'
                            }`}
                          >{label}</button>
                        )
                      })}
                      {showResult && (
                        <span className={`text-xs font-medium ${
                          isSubCorrect ? 'text-emerald-600'
                          : isSubWrong ? 'text-red-600'
                          : 'text-gray-400'
                        }`}>
                          {isSubCorrect
                            ? '✓ Chính xác'
                            : isSubWrong
                            ? `✗ Đáp án: ${correctChar === 'D' ? 'Đúng' : 'Sai'}`
                            : '—'}
                        </span>
                      )}
                    </div>
                  </div>
                )
              })
            : /* fallback: no options dict */
              <div className="flex gap-3">
                {['Đúng', 'Sai'].map(val => {
                  const isSelected = selectedAnswer === val
                  const isCorrectOpt = showResult && question.correct_answer === val
                  const isWrongOpt = showResult && isSelected && !isCorrectOpt
                  return (
                    <button
                      key={val}
                      onClick={() => !showResult && onAnswer(question.id, val)}
                      disabled={showResult}
                      className={`flex-1 py-3 rounded-xl border-2 font-semibold text-sm transition-all ${
                        isCorrectOpt ? 'border-emerald-400 bg-emerald-50 text-emerald-700'
                        : isWrongOpt ? 'border-red-400 bg-red-50 text-red-700'
                        : isSelected ? 'border-navy bg-navy text-white'
                        : 'border-gray-200 text-gray-600 hover:border-navy hover:bg-navy-50'
                      }`}
                    >{val}</button>
                  )
                })}
              </div>
          }
        </div>
      )}

      {/* ── Tự luận ── */}
      {question.question_type === 'tu_luan' && (
        <textarea
          disabled={showResult}
          value={selectedAnswer || ''}
          onChange={e => onAnswer(question.id, e.target.value)}
          placeholder="Nhập câu trả lời của bạn..."
          rows={4}
          className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl text-sm text-gray-700 focus:outline-none focus:border-navy resize-none bg-gray-50 focus:bg-white transition-colors disabled:opacity-60"
        />
      )}

      {/* Correct answer hint — skip dung_sai (shown per-row above) */}
      {showResult && isWrong && question.correct_answer && question.question_type !== 'dung_sai' && (
        <div className="mt-3 p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-sm text-emerald-700">
          <span className="font-semibold">Đáp án đúng:</span> {question.correct_answer}
        </div>
      )}
    </div>
  )
}
