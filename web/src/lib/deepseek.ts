import OpenAI from 'openai'
import type { DraftQuestion } from './teacher-types'

const CHUNK_SIZE = 10_000
const CONCURRENCY = 5

function getDeepSeek() {
  const apiKey = process.env.DEEPSEEK_API_KEY
  if (!apiKey) throw new Error('DEEPSEEK_API_KEY not set')
  return new OpenAI({
    apiKey,
    baseURL: 'https://api.deepseek.com',
  })
}

// ── BƯỚC 1: Chuẩn hóa Markdown → EXAM-TAG-12 ────────────────────────────────

const NORMALIZE_SYSTEM = `Bạn là chuyên gia xử lý đề thi Toán THPT Việt Nam.
Nhiệm vụ: nhận đoạn Markdown thô từ MinerU OCR và chuẩn hóa theo bộ quy tắc EXAM-TAG-12.

QUY TẮC EXAM-TAG-12 (TUYỆT ĐỐI tuân thủ):
1. Tiêu đề 3 phần: ==PHAN 1==  ==PHAN 2==  ==PHAN 3== — mỗi cái trên dòng riêng.
2. Đầu mỗi câu hỏi: [CAU 1]  [CAU 2]  ...  [CAU N] — bắt buộc ở đầu dòng mới.
3. Đáp án trắc nghiệm (Phần I): [A].   [B].   [C].   [D].  — mỗi cái xuống dòng.
4. Ý đúng/sai (Phần II): [a].   [b].   [c].   [d].  — mỗi cái xuống dòng.
5. Nếu tìm thấy bảng đáp án cuối đề: khớp đáp án vào cuối mỗi câu dưới dạng [DAPAN: X]
   (X ví dụ: A, B, DSDD, 1.5). Đặt ngay sau nội dung câu, trước [CAU N+1].
6. GIỮ NGUYÊN 100% công thức LaTeX ($...$, $$...$$) và thẻ ảnh ![](images/...).
7. Sửa lỗi OCR (chữ dính, ký tự vỡ, thiếu dấu tiếng Việt) nhưng KHÔNG thêm/bỏ câu.
8. KHÔNG giải thích, KHÔNG thêm tiêu đề markdown khác, KHÔNG bình luận.
9. Nếu sau nội dung câu xuất hiện "Lời giải", "Hướng dẫn giải", "Giải:":
   - KHÔNG tạo thêm [CAU N+1] mới. Đặt toàn bộ vào: [LOIGIAI: <nội dung>]
   - Tag [LOIGIAI:...] nằm SAU [DAPAN:...] (nếu có) và TRƯỚC [CAU N+1] tiếp theo.`

// ── BƯỚC 3: Trích xuất JSON từng câu ────────────────────────────────────────

const EXTRACT_SYSTEM = `Bạn là chuyên gia phân tích câu hỏi thi Toán THPT Việt Nam.
Nhiệm vụ: nhận nội dung 1 câu hỏi (đã chuẩn hóa EXAM-TAG-12) và trích xuất JSON.

Trả về DUY NHẤT 1 JSON object với các trường:
{
  "question_text": "Nội dung đề bài (giữ LaTeX và link ảnh nguyên vẹn, KHÔNG bao gồm phần [LOIGIAI:])",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "correct_answer": "Đáp án (ví dụ: A | DSDD | 1.5 | null nếu không có [DAPAN])",
  "explanation": "Nội dung bên trong [LOIGIAI: ...] nếu có, null nếu không",
  "topic": "Chủ đề toán (Hàm số, Tích phân, Hình học không gian, Xác suất...)",
  "level": "Nhận biết|Thông hiểu|Vận dụng|Vận dụng cao"
}

Lưu ý:
- options: mảng rỗng [] nếu là câu tự luận (Phần III)
- Phần II (đúng/sai): options gồm ["a. ...", "b. ...", "c. ...", "d. ..."]
- correct_answer: lấy từ [DAPAN: X] nếu có, không thì null`

// ── Helpers ─────────────────────────────────────────────────────────────────

function splitIntoChunks(text: string, maxSize: number): string[] {
  if (text.length <= maxSize) return [text]
  const paragraphs = text.split('\n\n')
  const chunks: string[] = []
  let current = ''
  for (const para of paragraphs) {
    if (current.length + para.length + 2 > maxSize && current) {
      chunks.push(current.trim())
      current = para
    } else {
      current = current ? current + '\n\n' + para : para
    }
  }
  if (current) chunks.push(current.trim())
  return chunks
}

function extractTailContext(normalized: string): string {
  const phanMatches = [...normalized.matchAll(/==PHAN\s*(\d+)==/gi)]
  const cauMatches = [...normalized.matchAll(/\[CAU\s+(\d+)\]/gi)]
  const lastPhan = phanMatches.at(-1)?.[0] ?? ''
  const lastCau = cauMatches.at(-1)?.[0] ?? ''
  if (lastPhan && lastCau) return `đang ở ${lastPhan}, vừa xử lý xong ${lastCau}`
  if (lastPhan) return `đang ở ${lastPhan}`
  return ''
}

function repairJson(raw: string): Record<string, unknown> | null {
  // 1. Parse thẳng
  try { return JSON.parse(raw) } catch {}

  // 2. Trích JSON object từ response
  const m = raw.match(/\{[\s\S]+\}/)
  if (!m) return null

  try { return JSON.parse(m[0]) } catch {}

  // 3. Sửa escape LaTeX phổ biến
  const fixed = m[0].replace(/(?<!\\)\\([^\\/"bfnrtu\n])/g, '\\\\$1')
  try { return JSON.parse(fixed) } catch {}

  return null
}

// ── Exported functions ────────────────────────────────────────────────────────

export async function normalizeMarkdown(
  rawText: string,
  onProgress?: (current: number, total: number) => void
): Promise<string> {
  const deepseek = getDeepSeek()
  const chunks = splitIntoChunks(rawText, CHUNK_SIZE)
  const parts: string[] = []
  let prevContext = ''

  for (let i = 0; i < chunks.length; i++) {
    onProgress?.(i + 1, chunks.length)
    const chunk = chunks[i]
    const userContent = prevContext
      ? `CONTEXT (đoạn trước kết thúc ở): ${prevContext}\n\nTiếp tục chuẩn hóa đoạn markdown này (KHÔNG lặp lại context, tiếp nối đúng phần/số câu từ context):\n\n${chunk}`
      : `Chuẩn hóa đoạn markdown sau theo EXAM-TAG-12. Chỉ trả về markdown đã chuẩn hóa, không có gì khác:\n\n${chunk}`

    try {
      const resp = await deepseek.chat.completions.create({
        model: 'deepseek-chat',
        temperature: 0,
        max_tokens: 4096,
        messages: [
          { role: 'system', content: NORMALIZE_SYSTEM },
          { role: 'user', content: userContent },
        ],
      })
      const result = resp.choices[0].message.content?.trim() ?? ''
      parts.push(result)
      prevContext = extractTailContext(result)
    } catch {
      parts.push(chunk)
      prevContext = ''
    }
  }

  return parts.join('\n\n')
}

export interface RawQuestion {
  part: string
  question_index: number
  raw_content: string
}

export function splitNormalizedText(normalizedText: string): RawQuestion[] {
  const partPat = /==PHAN\s*(\d+)==/gi
  const splits = [...normalizedText.matchAll(partPat)]

  const partsMap = new Map<number, string>()
  let maxSeen = 0

  for (let i = 0; i < splits.length; i++) {
    const partNum = parseInt(splits[i][1])
    const start = splits[i].index! + splits[i][0].length
    const end = i + 1 < splits.length ? splits[i + 1].index! : normalizedText.length
    const text = normalizedText.slice(start, end).trim()

    if (partNum > maxSeen) {
      maxSeen = partNum
      partsMap.set(partNum, text)
    } else {
      const existing = partsMap.get(maxSeen) ?? ''
      partsMap.set(maxSeen, existing + '\n\n' + text)
    }
  }

  if (partsMap.size === 0) partsMap.set(1, normalizedText)

  const questions: RawQuestion[] = []
  for (const partNum of [...partsMap.keys()].sort()) {
    const partText = partsMap.get(partNum)!
    const cauPat = /(?:^|\n)\s*\[CAU\s+(\d+)\]/gi
    const matches = [...partText.matchAll(cauPat)]

    for (let i = 0; i < matches.length; i++) {
      const qNum = parseInt(matches[i][1])
      const start = matches[i].index!
      const end = i + 1 < matches.length ? matches[i + 1].index! : partText.length
      const rawContent = partText.slice(start, end).trim()

      questions.push({
        part: `part_${partNum}`,
        question_index: qNum,
        raw_content: rawContent,
      })
    }
  }

  return questions
}

const PART_TO_QTYPE: Record<string, DraftQuestion['question_type']> = {
  part_1: 'trac_nghiem',
  part_2: 'dung_sai',
  part_3: 'tu_luan',
}

const LEVEL_MAP: Record<string, string> = {
  'nhận biết':    'Nhận biết',
  'thong hieu':   'Thông hiểu',
  'thông hiểu':   'Thông hiểu',
  'vận dụng cao': 'Vận dụng cao',
  'van dung cao': 'Vận dụng cao',
  'vận dụng':     'Vận dụng',
}

function normalizeLevel(raw: string): string {
  const key = raw.toLowerCase().trim()
  return LEVEL_MAP[key] ?? 'Nhận biết'
}

export async function extractQuestions(
  rawQuestions: RawQuestion[],
  draftExamId: string,
  onProgress?: (current: number, total: number) => void
): Promise<Omit<DraftQuestion, 'id' | 'created_at' | 'updated_at'>[]> {
  const deepseek = getDeepSeek()
  const results: (Omit<DraftQuestion, 'id' | 'created_at' | 'updated_at'> | null)[] = []

  // Process with concurrency limit
  const semaphore = { running: 0, queue: [] as (() => void)[] }

  const acquire = () => new Promise<void>(resolve => {
    if (semaphore.running < CONCURRENCY) {
      semaphore.running++
      resolve()
    } else {
      semaphore.queue.push(() => { semaphore.running++; resolve() })
    }
  })

  const release = () => {
    semaphore.running--
    const next = semaphore.queue.shift()
    if (next) next()
  }

  let completed = 0

  const tasks = rawQuestions.map(async (q, idx) => {
    await acquire()
    try {
      const resp = await deepseek.chat.completions.create({
        model: 'deepseek-chat',
        temperature: 0,
        max_tokens: 2048,
        response_format: { type: 'json_object' },
        messages: [
          { role: 'system', content: EXTRACT_SYSTEM },
          { role: 'user', content: `Trích xuất JSON từ câu hỏi sau:\n\n${q.raw_content}` },
        ],
      })

      const rawJson = resp.choices[0].message.content ?? ''
      const parsed = repairJson(rawJson)
      completed++
      onProgress?.(completed, rawQuestions.length)

      if (!parsed) {
        results[idx] = null
        return
      }

      const optionsRaw = (parsed.options as string[]) ?? []
      const optionsObj: Record<string, string> = {}
      for (const opt of optionsRaw) {
        const m = opt.match(/^([A-Da-d])[.)]\s*(.+)/)
        if (m) optionsObj[m[1].toUpperCase()] = m[2].trim()
      }

      results[idx] = {
        draft_exam_id:      draftExamId,
        question_number:    q.question_index,
        question_type:      PART_TO_QTYPE[q.part] ?? 'trac_nghiem',
        content:            String(parsed.question_text ?? '').trim(),
        options:            Object.keys(optionsObj).length > 0 ? optionsObj : null,
        correct_answer:     parsed.correct_answer ? String(parsed.correct_answer) : null,
        difficulty_level:   normalizeLevel(String(parsed.level ?? '')),
        topic:              parsed.topic ? String(parsed.topic).trim() : null,
        source_question_id: null,
      }
    } catch {
      completed++
      results[idx] = null
    } finally {
      release()
    }
  })

  await Promise.all(tasks)
  return results.filter((r): r is NonNullable<typeof r> => r !== null)
}
