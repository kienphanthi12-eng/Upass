import { NextRequest, NextResponse } from 'next/server'
import { createServerSupabase } from '@/lib/supabase-server'
import { normalizeMarkdown } from '@/lib/deepseek'

export const maxDuration = 300

export async function POST(
  _req: NextRequest,
  { params }: { params: Promise<{ jobId: string }> }
) {
  const { jobId } = await params
  const supabase = await createServerSupabase()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { data: job } = await supabase
    .from('ocr_jobs')
    .select('id, markdown, normalized_markdown, status, updated_at, teacher_id')
    .eq('id', jobId)
    .eq('teacher_id', user.id)
    .single()

  if (!job) return NextResponse.json({ error: 'Job không tồn tại' }, { status: 404 })
  if (!job.markdown) return NextResponse.json({ error: 'Chưa có markdown từ OCR' }, { status: 400 })

  // Nếu đã chuẩn hóa rồi thì trả về luôn
  if (job.normalized_markdown && (job.status === 'normalized' || job.status === 'done')) {
    return NextResponse.json({ ok: true })
  }

  // Nếu đang normalizing → chỉ retry nếu đã bị stale > 2 phút (serverless timeout)
  if (job.status === 'normalizing') {
    const updatedMs = new Date(job.updated_at).getTime()
    const staleSec = (Date.now() - updatedMs) / 1000
    if (staleSec < 120) {
      // Đang chạy thực sự → báo client tiếp tục chờ
      return NextResponse.json({ ok: true, pending: true })
    }
    // Stale → cho phép chạy lại bên dưới
  }

  try {
    await supabase
      .from('ocr_jobs')
      .update({ status: 'normalizing', updated_at: new Date().toISOString() })
      .eq('id', jobId)

    const normalizedMd = await normalizeMarkdown(job.markdown)

    await supabase
      .from('ocr_jobs')
      .update({
        normalized_markdown: normalizedMd,
        status: 'normalized',
        updated_at: new Date().toISOString(),
      })
      .eq('id', jobId)

    return NextResponse.json({ ok: true })
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    await supabase
      .from('ocr_jobs')
      .update({ status: 'error', error_msg: msg, updated_at: new Date().toISOString() })
      .eq('id', jobId)
    return NextResponse.json({ error: msg }, { status: 500 })
  }
}

