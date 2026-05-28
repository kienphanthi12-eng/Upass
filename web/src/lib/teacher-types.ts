export type OcrJobStatus =
  | 'pending'
  | 'uploading'
  | 'ocr_running'
  | 'ocr_done'
  | 'normalizing'
  | 'normalized'
  | 'extracting'
  | 'done'
  | 'error'

export interface OcrJob {
  id: string
  teacher_id: string
  filename: string
  status: OcrJobStatus
  mineru_batch_id: string | null
  markdown: string | null
  normalized_markdown: string | null
  pdf_storage_path: string | null
  error_msg: string | null
  question_count: number | null
  created_at: string
  updated_at: string
}

export interface DraftExam {
  id: string
  teacher_id: string
  ocr_job_id: string | null
  title: string
  exam_year: number
  exam_type: string
  subject_id: number
  status: 'draft' | 'published'
  published_exam_id: number | null
  created_at: string
  updated_at: string
  draft_questions?: DraftQuestion[]
}

export interface DraftQuestion {
  id: string
  draft_exam_id: string
  question_number: number | null
  question_type: 'trac_nghiem' | 'dung_sai' | 'tu_luan'
  content: string
  options: Record<string, string> | null
  correct_answer: string | null
  difficulty_level: string
  topic: string | null
  source_question_id: string | null
  created_at: string
  updated_at: string
}

export interface Assignment {
  id: string
  exam_id: number
  teacher_id: string
  assigned_to: string
  created_at: string
}

export interface Teacher {
  id: string
  full_name: string
  email: string | null
  created_at: string
}

export const OCR_STATUS_LABELS: Record<OcrJobStatus, string> = {
  pending:      'Chờ xử lý',
  uploading:    'Đang tải lên MinerU',
  ocr_running:  'MinerU đang đọc PDF',
  ocr_done:     'Đọc PDF xong, chuẩn hóa nội dung',
  normalizing:  'DeepSeek đang chuẩn hóa nội dung',
  normalized:   'Chuẩn hóa xong, sẵn sàng chỉnh sửa',
  extracting:   'Đang trích xuất câu hỏi',
  done:         'Hoàn tất',
  error:        'Lỗi',
}

export const EXAM_TYPE_OPTIONS = [
  { value: 'thi_thu',  label: 'Đề thi thử' },
  { value: 'KS',       label: 'Đề khảo sát' },
  { value: 'on_thi',   label: 'Đề ôn thi' },
  { value: 'GK',       label: 'Kiểm tra giữa kỳ' },
  { value: 'CK',       label: 'Kiểm tra cuối kỳ' },
  { value: 'THPT_QG',  label: 'THPT Quốc Gia' },
]

export const DIFFICULTY_OPTIONS = [
  'Nhận biết',
  'Thông hiểu',
  'Vận dụng',
  'Vận dụng cao',
]
