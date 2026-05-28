'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase'
import { EXAM_TYPE_OPTIONS, DIFFICULTY_OPTIONS } from '@/lib/teacher-types'
import type { MatrixCell, CellFeasibility } from '@/lib/matrix'

// ─── Types ────────────────────────────────────────────────────────────────────

interface TopicRow {
  id: number
  name: string
  parent_id: number | null
  levels: { level: string; count: number }[]
  total: number
}

interface SubjectStat {
  level: string
  count: number
}

interface Subject {
  id: number
  code: string
  name: string
}

// Cell value in the UI grid: (topic_id | null) × level → count input
type GridKey = `${string}__${string}` // `${topicId}__${level}`

// ─── Constants ────────────────────────────────────────────────────────────────

const LEVELS = DIFFICULTY_OPTIONS
const LEVEL_ABBR: Record<string, string> = {
  'Nhận biết':    'NB',
  'Thông hiểu':   'TH',
  'Vận dụng':     'VD',
  'Vận dụng cao': 'VDC',
}
const LEVEL_COLOR: Record<string, { bg: string; text: string; border: string }> = {
  'Nhận biết':    { bg: '#e8f4e8', text: '#2d6a2d', border: '#b3d9b3' },
  'Thông hiểu':   { bg: '#e8f0fb', text: '#2952a3', border: '#aec6f0' },
  'Vận dụng':     { bg: '#fff8e1', text: '#7a5c00', border: '#f0d87a' },
  'Vận dụng cao': { bg: '#fde8e0', text: '#a03010', border: '#f0b09a' },
}

// ─── Cell feasibility color logic ─────────────────────────────────────────────

function cellColor(available: number, required: number): { bg: string; dot: string } {
  if (required === 0) return { bg: 'transparent', dot: '#d4cfc4' }
  const ratio = available / required
  if (ratio >= 1)   return { bg: '#eef4e8', dot: '#4a5d3a' }   // green — ok
  if (ratio >= 0.5) return { bg: '#fdf7e3', dot: '#a8851f' }   // yellow — partial
  return              { bg: '#fdeee8', dot: '#b54a2b' }         // red — insufficient
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function MatrixPage() {
  const router = useRouter()
  const supabase = createClient()

  // Subject selection
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [subjectId, setSubjectId] = useState<number | null>(null)

  // Topic data
  const [topics, setTopics] = useState<TopicRow[]>([])
  const [subjectStats, setSubjectStats] = useState<SubjectStat[]>([])
  const [loadingTopics, setLoadingTopics] = useState(false)

  // Selected topics to display in grid
  const [selectedTopics, setSelectedTopics] = useState<TopicRow[]>([])

  // Grid values: GridKey → count (string for input, converted to number when needed)
  const [grid, setGrid] = useState<Record<GridKey, string>>({})

  // Feasibility
  const [feasibility, setFeasibility] = useState<Record<GridKey, CellFeasibility>>({})
  const [checkLoading, setCheckLoading] = useState(false)

  // Generate options
  const [title, setTitle] = useState('')
  const [examType, setExamType] = useState('thi_thu')
  const [examYear, setExamYear] = useState(new Date().getFullYear())
  const [variants, setVariants] = useState(1)

  // Generation state
  const [generating, setGenerating] = useState(false)
  const [genResult, setGenResult] = useState<string[] | null>(null)
  const [genError, setGenError] = useState<string | null>(null)

  // ── Load subjects ──────────────────────────────────────────────────────────

  useEffect(() => {
    supabase
      .from('subjects')
      .select('id, code, name')
      .order('name')
      .then(({ data }) => {
        if (data) setSubjects(data)
      })
  }, [])

  // ── Load topics khi chọn môn ──────────────────────────────────────────────

  useEffect(() => {
    if (!subjectId) { setTopics([]); return }
    setLoadingTopics(true)
    fetch(`/api/teacher/matrix/topics?subject_id=${subjectId}`)
      .then(r => r.json())
      .then(data => {
        setTopics(data.topics ?? [])
        setSubjectStats(data.subject_stats ?? [])
        setSelectedTopics([])
        setGrid({})
        setFeasibility({})
      })
      .finally(() => setLoadingTopics(false))
  }, [subjectId])

  // ── Helpers ───────────────────────────────────────────────────────────────

  const gridKey = (topicId: number | null, level: string): GridKey =>
    `${topicId ?? 'null'}__${level}`

  const getCellCount = (topicId: number | null, level: string): number => {
    const v = grid[gridKey(topicId, level)]
    const n = parseInt(v ?? '0')
    return isNaN(n) || n < 0 ? 0 : n
  }

  const totalQuestions = useCallback(() => {
    return selectedTopics.reduce((sum, t) =>
      sum + LEVELS.reduce((s, l) => s + getCellCount(t.id, l), 0)
    , 0)
  }, [selectedTopics, grid])

  // ── Feasibility check (debounced khi grid thay đổi) ──────────────────────

  useEffect(() => {
    if (!subjectId || selectedTopics.length === 0) return
    const cells = buildCells()
    if (cells.length === 0) return

    const t = setTimeout(async () => {
      setCheckLoading(true)
      try {
        const res = await fetch('/api/teacher/matrix/check', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ subject_id: subjectId, cells }),
        })
        const data = await res.json()
        const map: Record<GridKey, CellFeasibility> = {}
        for (const c of data.cells ?? []) {
          map[gridKey(c.topic_id, c.level)] = c
        }
        setFeasibility(map)
      } finally {
        setCheckLoading(false)
      }
    }, 600)

    return () => clearTimeout(t)
  }, [grid, selectedTopics, subjectId])

  // ── Build cells array ─────────────────────────────────────────────────────

  function buildCells(): MatrixCell[] {
    const cells: MatrixCell[] = []
    for (const topic of selectedTopics) {
      for (const level of LEVELS) {
        const count = getCellCount(topic.id, level)
        if (count > 0) {
          cells.push({ topic_id: topic.id, topic_name: topic.name, level, count })
        }
      }
    }
    return cells
  }

  // ── Toggle topic in/out of grid ───────────────────────────────────────────

  function toggleTopic(topic: TopicRow) {
    setSelectedTopics(prev => {
      const exists = prev.find(t => t.id === topic.id)
      if (exists) {
        // Remove: clean grid values
        const newGrid = { ...grid }
        LEVELS.forEach(l => delete newGrid[gridKey(topic.id, l)])
        setGrid(newGrid)
        return prev.filter(t => t.id !== topic.id)
      }
      return [...prev, topic]
    })
  }

  // ── Generate ──────────────────────────────────────────────────────────────

  async function handleGenerate() {
    if (!subjectId || !title.trim()) return
    const cells = buildCells()
    if (cells.length === 0) return

    setGenerating(true)
    setGenResult(null)
    setGenError(null)

    try {
      const res = await fetch('/api/teacher/matrix/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ subject_id: subjectId, cells, variants, title, exam_type: examType, exam_year: examYear }),
      })
      const data = await res.json()
      if (!res.ok) {
        setGenError(data.details ? data.details.join('\n') : (data.error ?? 'Lỗi không xác định'))
      } else {
        setGenResult(data.draft_exam_ids)
      }
    } catch (e) {
      setGenError(String(e))
    } finally {
      setGenerating(false)
    }
  }

  // ── Tổng số câu theo level (summary row) ──────────────────────────────────
  const totalByLevel = (level: string) =>
    selectedTopics.reduce((s, t) => s + getCellCount(t.id, level), 0)

  // ─────────────────────────────────────────────────────────────────────────
  // Render
  // ─────────────────────────────────────────────────────────────────────────

  return (
    <div style={{ padding: '2rem', maxWidth: 1200, margin: '0 auto' }}>

      {/* ── Header ── */}
      <div style={{ marginBottom: '2.5rem' }}>
        <p style={{ fontSize: 11, letterSpacing: '0.18em', textTransform: 'uppercase', color: '#6b6a66', margin: 0 }}>
          Công cụ giáo viên
        </p>
        <h1 style={{ fontFamily: 'var(--font-serif)', fontSize: 32, fontWeight: 400, letterSpacing: '-0.02em', color: '#1a1814', margin: '8px 0 6px' }}>
          Tạo đề từ <em style={{ fontStyle: 'italic' }}>ma trận</em>
        </h1>
        <p style={{ color: '#6b6a66', fontSize: 14, margin: 0 }}>
          Chọn chủ đề, điền số câu theo mức độ, hệ thống tự động chọn câu từ ngân hàng.
        </p>
      </div>

      {/* ── Step 1: Chọn môn ── */}
      <Section label="01" title="Chọn môn học">
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          {subjects.map(s => (
            <button
              key={s.id}
              id={`subject-${s.id}`}
              onClick={() => setSubjectId(s.id)}
              style={{
                padding: '8px 18px', fontSize: 13,
                border: subjectId === s.id ? '1px solid #1a1814' : '1px solid #d4cfc4',
                background: subjectId === s.id ? '#1a1814' : 'transparent',
                color: subjectId === s.id ? '#f5f1ea' : '#1a1814',
                cursor: 'pointer', transition: 'all .15s',
                letterSpacing: '0.08em',
              }}
            >
              {s.name}
            </button>
          ))}
        </div>
      </Section>

      {/* ── Step 2: Chọn chủ đề ── */}
      {subjectId && (
        <Section label="02" title="Chọn chủ đề đưa vào ma trận">
          {loadingTopics ? (
            <p style={{ color: '#6b6a66', fontSize: 13 }}>Đang tải…</p>
          ) : topics.length === 0 ? (
            <p style={{ color: '#b54a2b', fontSize: 13 }}>
              Môn này chưa có dữ liệu chủ đề trong ngân hàng câu.
            </p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {topics.map(topic => {
                const selected = !!selectedTopics.find(t => t.id === topic.id)
                return (
                  <button
                    key={topic.id}
                    id={`topic-${topic.id}`}
                    onClick={() => toggleTopic(topic)}
                    style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                      padding: '10px 16px', textAlign: 'left',
                      border: selected ? '1px solid #4a5d3a' : '1px solid #d4cfc4',
                      background: selected ? '#eef4e8' : '#f5f1ea',
                      cursor: 'pointer', transition: 'all .15s',
                    }}
                  >
                    <span style={{ fontSize: 13, color: selected ? '#2d4a20' : '#1a1814' }}>
                      {selected ? '✓ ' : ''}{topic.name}
                    </span>
                    <span style={{ display: 'flex', gap: 8 }}>
                      {LEVELS.map(l => {
                        const lvlData = topic.levels.find(x => x.level === l)
                        const cnt = lvlData?.count ?? 0
                        return cnt > 0 ? (
                          <span key={l} style={{
                            fontSize: 11, padding: '2px 7px',
                            background: LEVEL_COLOR[l].bg,
                            color: LEVEL_COLOR[l].text,
                            border: `1px solid ${LEVEL_COLOR[l].border}`,
                          }}>
                            {LEVEL_ABBR[l]} {cnt}
                          </span>
                        ) : null
                      })}
                    </span>
                  </button>
                )
              })}
            </div>
          )}
        </Section>
      )}

      {/* ── Step 3: Ma trận (grid) ── */}
      {selectedTopics.length > 0 && (
        <Section label="03" title="Nhập số câu theo ma trận">
          <div style={{ overflowX: 'auto' }}>
            <table style={{ borderCollapse: 'collapse', width: '100%', minWidth: 600 }}>
              <thead>
                <tr>
                  <th style={thStyle('left')}>Chủ đề</th>
                  {LEVELS.map(l => (
                    <th key={l} style={{
                      ...thStyle('center'),
                      background: LEVEL_COLOR[l].bg,
                      color: LEVEL_COLOR[l].text,
                      borderBottom: `2px solid ${LEVEL_COLOR[l].border}`,
                    }}>
                      {l}
                    </th>
                  ))}
                  <th style={thStyle('center')}>Tổng</th>
                </tr>
              </thead>
              <tbody>
                {selectedTopics.map((topic, ti) => (
                  <tr key={topic.id} style={{ background: ti % 2 === 0 ? '#f5f1ea' : '#ebe6dc' }}>
                    <td style={{ ...tdStyle('left'), fontWeight: 500, fontSize: 13 }}>
                      {topic.name}
                    </td>
                    {LEVELS.map(l => {
                      const key = gridKey(topic.id, l)
                      const feas = feasibility[key]
                      const count = getCellCount(topic.id, l)
                      const avail = topic.levels.find(x => x.level === l)?.count ?? 0
                      const colors = feas
                        ? cellColor(feas.available, feas.required)
                        : cellColor(avail, count)

                      return (
                        <td key={l} style={{ ...tdStyle('center'), background: count > 0 ? colors.bg : 'transparent', transition: 'background .2s' }}>
                          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3 }}>
                            <input
                              id={`cell-${topic.id}-${l}`}
                              type="number"
                              min={0}
                              value={grid[key] ?? ''}
                              placeholder="0"
                              onChange={e => setGrid(prev => ({ ...prev, [key]: e.target.value }))}
                              style={{
                                width: 56, textAlign: 'center', fontSize: 14, padding: '5px 6px',
                                border: `1px solid ${count > 0 ? colors.dot : '#d4cfc4'}`,
                                background: 'rgba(255,255,255,0.7)',
                                outline: 'none', color: '#1a1814',
                              }}
                            />
                            {count > 0 && (
                              <span style={{ fontSize: 10, color: colors.dot, letterSpacing: '0.05em' }}>
                                {feas
                                  ? `${feas.available} có sẵn`
                                  : `${avail} có sẵn`
                                }
                              </span>
                            )}
                          </div>
                        </td>
                      )
                    })}
                    <td style={{ ...tdStyle('center'), fontWeight: 600, color: '#4a5d3a' }}>
                      {LEVELS.reduce((s, l) => s + getCellCount(topic.id, l), 0)}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr style={{ borderTop: '2px solid #d4cfc4' }}>
                  <td style={{ ...tdStyle('left'), fontWeight: 600, letterSpacing: '0.1em', fontSize: 11, textTransform: 'uppercase', color: '#6b6a66' }}>
                    Tổng mỗi mức
                  </td>
                  {LEVELS.map(l => (
                    <td key={l} style={{ ...tdStyle('center'), fontWeight: 700, color: LEVEL_COLOR[l].text, background: LEVEL_COLOR[l].bg }}>
                      {totalByLevel(l) || '—'}
                    </td>
                  ))}
                  <td style={{ ...tdStyle('center'), fontWeight: 700, fontSize: 16, color: '#1a1814' }}>
                    {totalQuestions()}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>

          {/* Feasibility check indicator */}
          {checkLoading && (
            <p style={{ color: '#6b6a66', fontSize: 12, marginTop: 8 }}>
              ⟳ Đang kiểm tra ngân hàng câu…
            </p>
          )}
          {!checkLoading && Object.keys(feasibility).length > 0 && (() => {
            const allOk = Object.values(feasibility).every(c => c.ok)
            const bad   = Object.values(feasibility).filter(c => !c.ok)
            return allOk ? (
              <div style={{ marginTop: 12, padding: '10px 14px', background: '#eef4e8', border: '1px solid #b3d9b3', fontSize: 13, color: '#2d6a2d' }}>
                ✓ Ngân hàng đủ câu cho toàn bộ ma trận.
              </div>
            ) : (
              <div style={{ marginTop: 12, padding: '10px 14px', background: '#fdeee8', border: '1px solid #f0b09a', fontSize: 13, color: '#a03010' }}>
                ⚠ Thiếu câu ở {bad.length} ô:&nbsp;
                {bad.map(c => `"${c.topic_name}" ${c.level} (cần ${c.required}, có ${c.available})`).join(' · ')}
              </div>
            )
          })()}
        </Section>
      )}

      {/* ── Step 4: Cài đặt + Generate ── */}
      {selectedTopics.length > 0 && totalQuestions() > 0 && (
        <Section label="04" title="Cài đặt đề thi & tạo">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 16, marginBottom: 20 }}>
            <Field label="Tiêu đề đề thi">
              <input
                id="matrix-title"
                value={title}
                onChange={e => setTitle(e.target.value)}
                placeholder="Đề thi thử THPT Toán 2025"
                style={inputStyle}
              />
            </Field>

            <Field label="Loại đề">
              <select
                id="matrix-exam-type"
                value={examType}
                onChange={e => setExamType(e.target.value)}
                style={inputStyle}
              >
                {EXAM_TYPE_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </Field>

            <Field label="Năm học">
              <input
                id="matrix-exam-year"
                type="number"
                value={examYear}
                onChange={e => setExamYear(parseInt(e.target.value))}
                style={inputStyle}
              />
            </Field>

            <Field label="Số mã đề">
              <div style={{ display: 'flex', gap: 8 }}>
                {[1, 2, 3, 4].map(n => (
                  <button
                    key={n}
                    id={`variants-${n}`}
                    onClick={() => setVariants(n)}
                    style={{
                      flex: 1, padding: '8px 4px', fontSize: 13, fontWeight: 600,
                      border: variants === n ? '1px solid #1a1814' : '1px solid #d4cfc4',
                      background: variants === n ? '#1a1814' : 'transparent',
                      color: variants === n ? '#f5f1ea' : '#1a1814',
                      cursor: 'pointer', transition: 'all .15s',
                    }}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </Field>
          </div>

          {/* Summary */}
          <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', padding: '14px 18px', background: '#ebe6dc', border: '1px solid #d4cfc4', marginBottom: 20 }}>
            <Stat label="Tổng câu / đề" value={String(totalQuestions())} />
            <Stat label="Số mã đề" value={`${variants} mã (A${variants > 1 ? '–' + String.fromCharCode(64 + variants) : ''})`} />
            <Stat label="Chủ đề" value={String(selectedTopics.length)} />
          </div>

          {/* Error */}
          {genError && (
            <div style={{ padding: '12px 16px', background: '#fdeee8', border: '1px solid #f0b09a', color: '#a03010', fontSize: 13, marginBottom: 16, whiteSpace: 'pre-line' }}>
              ✕ {genError}
            </div>
          )}

          {/* Success */}
          {genResult && (
            <div style={{ padding: '16px 20px', background: '#eef4e8', border: '1px solid #b3d9b3', marginBottom: 16 }}>
              <p style={{ color: '#2d6a2d', fontWeight: 600, marginBottom: 10 }}>
                ✓ Tạo thành công {genResult.length} mã đề!
              </p>
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                {genResult.map((id, i) => (
                  <a
                    key={id}
                    href={`/teacher/drafts/${id}`}
                    style={{
                      display: 'inline-block', padding: '8px 18px', fontSize: 13,
                      background: '#1a1814', color: '#f5f1ea',
                      textDecoration: 'none', letterSpacing: '0.05em',
                    }}
                  >
                    Mã {String.fromCharCode(65 + i)} → Xem draft
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* Generate button */}
          {!genResult && (
            <button
              id="matrix-generate-btn"
              onClick={handleGenerate}
              disabled={generating || !title.trim() || totalQuestions() === 0}
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 10,
                padding: '13px 32px', fontSize: 14, fontWeight: 600,
                background: generating ? '#6b6a66' : '#1a1814',
                color: '#f5f1ea', border: 'none', cursor: generating ? 'wait' : 'pointer',
                letterSpacing: '0.08em', textTransform: 'uppercase',
                transition: 'background .2s', opacity: (!title.trim() || totalQuestions() === 0) ? 0.5 : 1,
              }}
            >
              {generating ? (
                <>
                  <Spinner /> Đang tạo {variants} mã đề…
                </>
              ) : (
                `Tạo ${variants} mã đề →`
              )}
            </button>
          )}
        </Section>
      )}
    </div>
  )
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function Section({ label, title, children }: { label: string; title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: '2.5rem' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, marginBottom: 16 }}>
        <span style={{ fontSize: 11, letterSpacing: '0.18em', textTransform: 'uppercase', color: '#a8a59f', fontFamily: 'var(--font-mono)' }}>
          ({label})
        </span>
        <h2 style={{ fontSize: 16, fontWeight: 600, color: '#1a1814', margin: 0, letterSpacing: '-0.01em' }}>
          {title}
        </h2>
      </div>
      {children}
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label style={{ display: 'block', fontSize: 11, letterSpacing: '0.18em', textTransform: 'uppercase', color: '#6b6a66', marginBottom: 6 }}>
        {label}
      </label>
      {children}
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div style={{ fontSize: 11, letterSpacing: '0.18em', textTransform: 'uppercase', color: '#6b6a66', marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700, color: '#1a1814', fontFamily: 'var(--font-mono)' }}>{value}</div>
    </div>
  )
}

function Spinner() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
      style={{ animation: 'spin 0.8s linear infinite' }}>
      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
    </svg>
  )
}

// ─── Styles ──────────────────────────────────────────────────────────────────

const inputStyle: React.CSSProperties = {
  width: '100%', padding: '8px 12px', fontSize: 13,
  border: '1px solid #d4cfc4', background: '#f5f1ea',
  color: '#1a1814', outline: 'none', boxSizing: 'border-box',
}

function thStyle(align: 'left' | 'center'): React.CSSProperties {
  return {
    padding: '10px 14px', textAlign: align, fontSize: 11,
    letterSpacing: '0.1em', textTransform: 'uppercase',
    color: '#6b6a66', border: '1px solid #d4cfc4',
    background: '#ebe6dc', fontWeight: 600, whiteSpace: 'nowrap',
  }
}

function tdStyle(align: 'left' | 'center'): React.CSSProperties {
  return {
    padding: '10px 14px', textAlign: align,
    border: '1px solid #d4cfc4', verticalAlign: 'middle',
  }
}
