import { NextRequest, NextResponse } from 'next/server'

const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN
const CHAT_ID = process.env.TELEGRAM_CHAT_ID

type NotifyEvent =
  | { type: 'register'; fullName: string; className?: string; email: string; role?: 'student' | 'teacher' }
  | { type: 'exam_start'; studentName: string; examTitle: string }
  | { type: 'exam_submit'; studentName: string; examTitle: string; score: number; correct: number; total: number }

function buildMessage(event: NotifyEvent): string {
  const now = new Date().toLocaleString('vi-VN', {
    timeZone: 'Asia/Ho_Chi_Minh',
    dateStyle: 'short',
    timeStyle: 'short',
  })

  switch (event.type) {
    case 'register':
      const title = event.role === 'teacher' ? '👨‍🏫 *Giáo viên mới đăng ký*' : '🎉 *Học sinh mới đăng ký*'
      return (
        `${title}\n\n` +
        `👤 *Tên:* ${event.fullName}\n` +
        (event.className ? `🏫 *Lớp:* ${event.className}\n` : '') +
        `📧 *Email:* ${event.email}\n` +
        `🕐 *Lúc:* ${now}`
      )

    case 'exam_start':
      return (
        `📝 *Bắt đầu làm bài thi*\n\n` +
        `👤 *Học sinh:* ${event.studentName}\n` +
        `📚 *Đề thi:* ${event.examTitle}\n` +
        `🕐 *Lúc:* ${now}`
      )

    case 'exam_submit':
      const pct = event.total > 0 ? Math.round((event.correct / event.total) * 100) : 0
      const emoji = pct >= 80 ? '🌟' : pct >= 60 ? '✅' : pct >= 40 ? '⚠️' : '❌'
      return (
        `${emoji} *Nộp bài hoàn thành*\n\n` +
        `👤 *Học sinh:* ${event.studentName}\n` +
        `📚 *Đề thi:* ${event.examTitle}\n` +
        `🎯 *Điểm:* ${event.score.toFixed(2)}/10 (${event.correct}/${event.total} câu đúng)\n` +
        `🕐 *Lúc:* ${now}`
      )
  }
}

export async function POST(req: NextRequest) {
  if (!BOT_TOKEN || !CHAT_ID) {
    return NextResponse.json({ error: 'Telegram not configured' }, { status: 500 })
  }

  let body: NotifyEvent
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 })
  }

  const text = buildMessage(body)

  try {
    const res = await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chat_id: CHAT_ID,
        text,
        parse_mode: 'Markdown',
      }),
    })

    if (!res.ok) {
      const err = await res.text()
      console.error('[Telegram notify] Error:', err)
      return NextResponse.json({ error: 'Telegram API error' }, { status: 502 })
    }

    return NextResponse.json({ ok: true })
  } catch (e) {
    console.error('[Telegram notify] Fetch error:', e)
    return NextResponse.json({ error: 'Network error' }, { status: 503 })
  }
}
