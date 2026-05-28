export type QuestionType = 'trac_nghiem' | 'dung_sai' | 'tu_luan'
export type Level = 'Nhận biết' | 'Thông hiểu' | 'Vận dụng' | 'Vận dụng cao'

export interface Subject {
  id: number
  code: string
  name: string
}

export interface Topic {
  id: number
  subject_id: number
  name: string
  parent_id: number | null
}

export interface Exam {
  id: number
  title: string
  display_title: string | null   // City-name encoding shown to users
  year: number
  exam_type: string
  subject_id: number
  total_pages: number | null
  created_at: string
  subjects?: Subject
  question_count?: number
}

/** Use this everywhere we show an exam name to users.
 *  Falls back to original title if display_title is unset. */
export function examDisplayName(exam: { title?: string | null; display_title?: string | null } | null | undefined): string {
  if (!exam) return ''
  return exam.display_title || exam.title || 'Đề thi'
}

export interface Question {
  id: number
  exam_id: number
  subject_id: number
  topic_id: number | null
  question_number: number
  content: string
  question_type: QuestionType
  level: Level
  options: Record<string, string> | null
  correct_answer: string | null
  has_formula: boolean
  has_image: boolean
  topics?: Topic
  subjects?: Subject
}

export interface Student {
  id: string
  full_name: string
  class_name: string | null
  student_code: string | null
  avatar_url: string | null
  created_at: string
}

export interface ExamSubmission {
  id: string
  student_id: string
  exam_id: number
  submitted_at: string
  time_taken: number | null
  score: number | null
  total_questions: number
  correct_count: number
  status: 'completed' | 'in_progress'
  exams?: Exam
}

export interface StudentAnswer {
  id: string
  submission_id: string
  question_id: number
  answer: string | null
  is_correct: boolean | null
}

export interface AnswerMap {
  [questionId: number]: string
}
