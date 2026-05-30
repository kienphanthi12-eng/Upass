/**
 * lib/matrix.ts
 * Core algorithms cho tính năng tạo ma trận đề thi.
 *
 * Phase 1: Stratified Sampling
 * Phase 2: Feasibility Check
 * Phase 3: Weighted Reservoir Sampling (chống lặp câu)
 * Phase 4: Multiple variant generation + Fisher-Yates shuffle
 */

import type { SupabaseClient } from '@supabase/supabase-js'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface MatrixCell {
  topic_id:   number | null   // null = "Tất cả chủ đề"
  topic_name: string
  level:      string          // 'Nhận biết' | 'Thông hiểu' | 'Vận dụng' | 'Vận dụng cao'
  count:      number          // Số câu cần lấy
}

export interface MatrixDef {
  subject_id: number
  cells:      MatrixCell[]
}

// Kết quả feasibility check cho 1 ô
export interface CellFeasibility {
  topic_id:   number | null
  topic_name: string
  level:      string
  required:   number
  available:  number
  ok:         boolean         // available >= required
}

export interface FeasibilityResult {
  feasible: boolean           // tất cả ô đều ok
  cells:    CellFeasibility[]
  total_required:  number
  total_available: number
}

// Câu hỏi đã chọn cho 1 đề
export interface SelectedQuestion {
  id:             number
  content:        string
  question_type:  string
  options:        Record<string, string> | null
  correct_answer: string | null
  level:          string
  topic_id:       number | null
  has_formula:    boolean
  has_image:      boolean
}

// ─── Phase 2: Feasibility Check ──────────────────────────────────────────────

export async function checkFeasibility(
  supabase: SupabaseClient,
  matrix: MatrixDef
): Promise<FeasibilityResult> {
  const cells: CellFeasibility[] = []

  for (const cell of matrix.cells) {
    if (cell.count === 0) continue

    let query = supabase
      .from('questions')
      .select('id', { count: 'exact', head: true })
      .eq('subject_id', matrix.subject_id)
      .eq('level', cell.level)
      .not('correct_answer', 'is', null)

    if (cell.topic_id !== null) {
      query = query.eq('topic_id', cell.topic_id)
    }

    const { count } = await query
    const available = count ?? 0

    cells.push({
      topic_id:   cell.topic_id,
      topic_name: cell.topic_name,
      level:      cell.level,
      required:   cell.count,
      available,
      ok:         available >= cell.count,
    })
  }

  const total_required  = cells.reduce((s, c) => s + c.required, 0)
  const total_available = cells.reduce((s, c) => s + c.available, 0)

  return {
    feasible: cells.every(c => c.ok),
    cells,
    total_required,
    total_available,
  }
}

// ─── Phase 3: Weighted Reservoir Sampling ────────────────────────────────────

/**
 * Weighted reservoir sampling (Algorithm A-Res by Efraimidis & Spirakis).
 * Câu được dùng gần đây → weight thấp hơn → ít có khả năng được chọn.
 */
function weightedReservoirSample<T>(
  items: T[],
  weights: number[],
  k: number
): T[] {
  if (items.length <= k) return [...items]

  // Reservoir: heap-like structure (min-heap by key)
  type Entry = { item: T; key: number }
  const reservoir: Entry[] = []

  for (let i = 0; i < items.length; i++) {
    const w = Math.max(weights[i], 1e-9)
    const key = Math.pow(Math.random(), 1 / w)

    if (reservoir.length < k) {
      reservoir.push({ item: items[i], key })
      if (reservoir.length === k) {
        reservoir.sort((a, b) => a.key - b.key) // min first
      }
    } else if (key > reservoir[0].key) {
      reservoir[0] = { item: items[i], key }
      // Bubble up the new minimum
      reservoir.sort((a, b) => a.key - b.key)
    }
  }

  return reservoir.map(e => e.item)
}

// ─── Phase 1 + 3: Stratified Sampling ────────────────────────────────────────

/**
 * Lấy câu hỏi từ DB theo ma trận, áp dụng weighted sampling.
 * usageMap: question_id → số lần dùng gần đây (30 ngày)
 */
async function stratifiedSample(
  supabase: SupabaseClient,
  matrix: MatrixDef,
  usageMap: Map<number, number>,
  excludeIds: Set<number> = new Set()
): Promise<SelectedQuestion[]> {
  const selected: SelectedQuestion[] = []

  for (const cell of matrix.cells) {
    if (cell.count === 0) continue

    let query = supabase
      .from('questions')
      .select('id, content, question_type, options, correct_answer, level, topic_id, has_formula, has_image')
      .eq('subject_id', matrix.subject_id)
      .eq('level', cell.level)
      .not('correct_answer', 'is', null)

    if (cell.topic_id !== null) {
      query = query.eq('topic_id', cell.topic_id)
    }

    const { data: candidates } = await query
    if (!candidates || candidates.length === 0) continue

    // Loại trừ câu đã chọn ở variants trước (nếu có)
    const pool = candidates.filter(q => !excludeIds.has(q.id))

    // Tính weight cho từng câu: càng ít dùng gần đây → weight cao hơn
    const weights = pool.map(q => {
      const usage = usageMap.get(q.id) ?? 0
      return 1 / (1 + usage)
    })

    // Weighted reservoir sampling
    const picked = weightedReservoirSample(pool, weights, cell.count)
    selected.push(...(picked as SelectedQuestion[]))

    // Thêm vào excludeIds để variants sau không trùng
    picked.forEach(q => excludeIds.add((q as SelectedQuestion).id))
  }

  return selected
}

// ─── Phase 4: Fisher-Yates shuffle ──────────────────────────────────────────

/** Xáo trộn thứ tự câu hỏi */
function shuffleArray<T>(arr: T[]): T[] {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

/**
 * Xáo trộn thứ tự đáp án A/B/C/D cho câu trắc nghiệm.
 * Cập nhật correct_answer để vẫn đúng sau khi xáo.
 */
function shuffleAnswers(q: SelectedQuestion): SelectedQuestion {
  if (q.question_type !== 'trac_nghiem' || !q.options) return q

  const keys = Object.keys(q.options)   // ['A','B','C','D']
  const values = keys.map(k => q.options![k])

  // Fisher-Yates trên values
  for (let i = values.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[values[i], values[j]] = [values[j], values[i]]
  }

  const correctValue = q.options[q.correct_answer ?? '']
  const newOptions: Record<string, string> = {}
  let newCorrect = q.correct_answer

  keys.forEach((k, i) => {
    newOptions[k] = values[i]
    if (values[i] === correctValue) newCorrect = k
  })

  return { ...q, options: newOptions, correct_answer: newCorrect }
}

// ─── Main: Generate Exam Variants ────────────────────────────────────────────

export interface GenerateOptions {
  matrix:    MatrixDef
  variants:  number      // 1-4
  title:     string
  exam_type: string
  exam_year: number
  teacher_id: string
}

export interface GenerateResult {
  draft_exam_ids: string[]
  total_questions: number
  usage_records: { question_id: number }[]
}

export async function generateExamVariants(
  supabase: SupabaseClient,
  opts: GenerateOptions
): Promise<GenerateResult> {
  const { matrix, variants, title, exam_type, exam_year, teacher_id } = opts

  // Phase 3: Load usage data (30 ngày gần nhất)
  const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString()
  const { data: usageRows } = await supabase
    .from('question_usage')
    .select('question_id')
    .eq('teacher_id', teacher_id)
    .gte('used_at', thirtyDaysAgo)

  const usageMap = new Map<number, number>()
  for (const row of usageRows ?? []) {
    usageMap.set(row.question_id, (usageMap.get(row.question_id) ?? 0) + 1)
  }

  const draft_exam_ids: string[] = []
  const allUsedIds: number[] = []
  const excludeIds = new Set<number>()

  // Phase 4: Tạo N variants
  for (let v = 0; v < variants; v++) {
    // Stratified sample (excludeIds để tránh trùng giữa variants nếu pool đủ lớn)
    const questions = await stratifiedSample(supabase, matrix, usageMap, excludeIds)

    // Xáo thứ tự câu + đáp án
    const shuffledQs = shuffleArray(questions).map(shuffleAnswers)

    // Tạo draft_exam
    const variantLabel = variants > 1 ? ` — Mã ${String.fromCharCode(65 + v)}` : ''
    const { data: exam, error: examErr } = await supabase
      .from('draft_exams')
      .insert({
        teacher_id,
        title: `${title}${variantLabel}`,
        exam_type,
        exam_year,
        subject_id: matrix.subject_id,
        status: 'draft',
        source: 'matrix',
      })
      .select('id')
      .single()

    if (examErr || !exam) {
      throw new Error(`Không tạo được draft exam variant ${v + 1}: ${examErr?.message}`)
    }

    // Insert draft_questions
    if (shuffledQs.length > 0) {
      const draftQuestions = shuffledQs.map((q, idx) => ({
        draft_exam_id:   exam.id,
        question_number: idx + 1,
        question_type:   q.question_type,
        content:         q.content,
        options:         q.options,
        correct_answer:  q.correct_answer,
        difficulty_level: q.level,
        source_question_id: q.id,   // reference back to original
      }))

      const { error: insertErr } = await supabase.from('draft_questions').insert(draftQuestions)
      if (insertErr) {
        throw new Error(`Lỗi lưu câu hỏi ma trận: ${insertErr.message}`)
      }
    }

    draft_exam_ids.push(exam.id)
    shuffledQs.forEach(q => allUsedIds.push(q.id))
  }

  // Phase 3: Ghi usage records
  const usageRecords = allUsedIds.map(qid => ({
    question_id: qid,
    teacher_id,
  }))

  if (usageRecords.length > 0) {
    await supabase.from('question_usage').insert(usageRecords)
  }

  return {
    draft_exam_ids,
    total_questions: allUsedIds.length / Math.max(variants, 1),
    usage_records: usageRecords,
  }
}
