'use client'

import { useState, useCallback } from 'react'
import katex from 'katex'

interface Props {
  value: string
  onChange: (v: string) => void
  placeholder?: string
  rows?: number
}

const HTML_TAG_RE = /<(table|thead|tbody|tr|td|th|img|br|ul|ol|li|p|div|span|b|strong|em|i)[^>]*>/i
const MD_IMAGE_RE = /!\[([^\]]*)\]\(([^)]+)\)/

/** Tách text có thể chứa ảnh markdown thành mảng [text|{alt,src}] */
function splitImages(text: string): Array<string | { alt: string; src: string }> {
  const result: Array<string | { alt: string; src: string }> = []
  const re = /!\[([^\]]*)\]\(([^)]+)\)/g
  let last = 0, m: RegExpExecArray | null
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) result.push(text.slice(last, m.index))
    result.push({ alt: m[1], src: m[2] })
    last = m.index + m[0].length
  }
  if (last < text.length) result.push(text.slice(last))
  return result
}

// Parse và render LaTeX + HTML + markdown images trong text
function RenderLatex({ text }: { text: string }) {
  if (!text) return <span className="text-gray-400 text-sm italic">Chưa có nội dung</span>

  // Tách LaTeX trước
  const parts = text.split(/((?:\$\$[\s\S]*?\$\$|\$[^$\n]+?\$))/g)

  return (
    <span>
      {parts.map((part, i) => {
        if (part.startsWith('$$') && part.endsWith('$$')) {
          const math = part.slice(2, -2)
          try {
            const html = katex.renderToString(math, { displayMode: true, throwOnError: false })
            return (
              <span key={i} className="katex-display-block inline-block w-full"
                dangerouslySetInnerHTML={{ __html: html.replace(/\r?\n/g, ' ') }}
              />
            )
          } catch {
            return <code key={i} className="text-red-500">{part}</code>
          }
        }
        if (part.startsWith('$') && part.endsWith('$')) {
          const math = part.slice(1, -1)
          try {
            const html = katex.renderToString(math, { displayMode: false, throwOnError: false })
            return (
              <span key={i} className="katex-inline-block"
                dangerouslySetInnerHTML={{ __html: html.replace(/\r?\n/g, ' ') }}
              />
            )
          } catch {
            return <code key={i} className="text-red-500">{part}</code>
          }
        }
        // Render HTML tags (tables từ OCR)
        if (HTML_TAG_RE.test(part)) {
          return (
            <span key={i} className="latex-html-block"
              dangerouslySetInnerHTML={{ __html: part }} />
          )
        }
        // Render markdown images ![alt](src)
        if (MD_IMAGE_RE.test(part)) {
          return (
            <span key={i}>
              {splitImages(part).map((chunk, j) => {
                if (typeof chunk === 'string') {
                  return chunk.split('\n').map((line, k, arr) => (
                    <span key={`${j}-${k}`}>{line}{k < arr.length - 1 && <br />}</span>
                  ))
                }
                return (
                  <img key={j} src={chunk.src} alt={chunk.alt}
                    className="max-w-full my-2 rounded border border-gray-200"
                    style={{ maxHeight: 300 }}
                  />
                )
              })}
            </span>
          )
        }
        // Plain text — render newlines
        return part.split('\n').map((line, j, arr) => (
          <span key={`${i}-${j}`}>
            {line}
            {j < arr.length - 1 && <br />}
          </span>
        ))
      })}
    </span>
  )
}

const LATEX_SHORTCUTS = [
  { label: 'Phân số', insert: '\\frac{}{}'  },
  { label: 'Căn',     insert: '\\sqrt{}'     },
  { label: 'Mũ',      insert: '^{}'          },
  { label: 'Chỉ số',  insert: '_{}'          },
  { label: '∞',       insert: '\\infty'      },
  { label: '±',       insert: '\\pm'         },
  { label: '×',       insert: '\\times'      },
  { label: '÷',       insert: '\\div'        },
  { label: '≤',       insert: '\\leq'        },
  { label: '≥',       insert: '\\geq'        },
  { label: '∑',       insert: '\\sum_{i=1}^{n}' },
  { label: '∫',       insert: '\\int_{0}^{1}' },
]

export default function LatexEditor({ value, onChange, placeholder, rows = 6 }: Props) {
  const [focused, setFocused] = useState(false)

  const insertAt = useCallback((snippet: string, el: HTMLTextAreaElement) => {
    const start = el.selectionStart
    const end = el.selectionEnd
    const newVal = value.slice(0, start) + snippet + value.slice(end)
    onChange(newVal)
    setTimeout(() => {
      el.focus()
      const cursor = start + snippet.indexOf('{}') + 1
      el.setSelectionRange(cursor > start ? cursor : start + snippet.length, cursor > start ? cursor : start + snippet.length)
    }, 0)
  }, [value, onChange])

  return (
    <div className="border-2 border-gray-200 rounded-xl overflow-hidden focus-within:border-navy transition-colors">
      {/* Toolbar */}
      <div className="flex flex-wrap gap-1 px-2 py-1.5 bg-gray-50 border-b border-gray-200">
        {LATEX_SHORTCUTS.map(s => (
          <button
            key={s.label}
            type="button"
            onClick={e => {
              const ta = e.currentTarget.closest('.editor-wrap')?.querySelector('textarea') as HTMLTextAreaElement
              if (ta) insertAt(s.insert, ta)
            }}
            className="px-2 py-1 text-xs font-mono bg-white border border-gray-200 rounded hover:bg-navy hover:text-white hover:border-navy transition-colors"
            title={s.insert}
          >
            {s.label}
          </button>
        ))}
        <span className="ml-auto text-xs text-gray-400 self-center px-1">
          Dùng $...$ cho LaTeX inline, $$...$$ cho block
        </span>
      </div>

      {/* Split view */}
      <div className="editor-wrap grid grid-cols-2 divide-x divide-gray-200">
        {/* Editor */}
        <textarea
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder ?? 'Nhập nội dung câu hỏi... (dùng $x^2$ cho LaTeX)'}
          rows={rows}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          className="w-full px-4 py-3 text-sm font-mono text-gray-800 bg-white resize-none focus:outline-none leading-relaxed"
          spellCheck={false}
        />

        {/* Preview */}
        <div className={`px-4 py-3 text-sm bg-white min-h-[${rows * 24}px] overflow-auto`}>
          <div className="text-xs font-medium text-gray-400 mb-1.5 uppercase tracking-wide">Preview</div>
          <div className="text-gray-800 leading-relaxed">
            <RenderLatex text={value} />
          </div>
        </div>
      </div>
    </div>
  )
}

export { RenderLatex }
