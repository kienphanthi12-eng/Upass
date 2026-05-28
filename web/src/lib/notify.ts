/**
 * Client-side helper để gửi thông báo Telegram.
 * Gọi server-side API route /api/notify — token không lộ ra client.
 */

type RegisterEvent = {
  type: 'register'
  fullName: string
  className?: string
  email: string
  role?: 'student' | 'teacher'
}

type ExamStartEvent = {
  type: 'exam_start'
  studentName: string
  examTitle: string
}

type ExamSubmitEvent = {
  type: 'exam_submit'
  studentName: string
  examTitle: string
  score: number
  correct: number
  total: number
}

type NotifyEvent = RegisterEvent | ExamStartEvent | ExamSubmitEvent

export async function notify(event: NotifyEvent): Promise<void> {
  try {
    await fetch('/api/notify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(event),
    })
  } catch (e) {
    // Không để lỗi notify làm crash flow chính
    console.warn('[notify] Failed to send Telegram notification:', e)
  }
}
