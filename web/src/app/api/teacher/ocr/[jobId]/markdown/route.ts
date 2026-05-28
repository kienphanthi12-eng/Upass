import { NextRequest, NextResponse } from 'next/server'
import { createServerSupabase } from '@/lib/supabase-server'

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ jobId: string }> }
) {
  const { jobId } = await params
  const supabase = await createServerSupabase()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { data: job } = await supabase
    .from('ocr_jobs')
    .select('id, filename, normalized_markdown, pdf_storage_path, teacher_id')
    .eq('id', jobId)
    .eq('teacher_id', user.id)
    .single()

  if (!job) return NextResponse.json({ error: 'Job không tồn tại' }, { status: 404 })

  // Tạo signed URL cho PDF (4 giờ) — dùng user auth, RLS cho phép
  let pdfUrl: string | null = null
  if (job.pdf_storage_path) {
    try {
      const { data } = await supabase.storage
        .from('teacher-pdfs')
        .createSignedUrl(job.pdf_storage_path, 14400)
      pdfUrl = data?.signedUrl ?? null
    } catch { /* PDF không bắt buộc */ }
  }

  const { data: draftExam } = await supabase
    .from('draft_exams')
    .select('id')
    .eq('ocr_job_id', jobId)
    .maybeSingle()

  return NextResponse.json({
    markdown: job.normalized_markdown ?? '',
    pdfUrl,
    filename: job.filename,
    draftExamId: draftExam?.id ?? null,
  })
}

export async function PUT(
  req: NextRequest,
  { params }: { params: Promise<{ jobId: string }> }
) {
  const { jobId } = await params
  const supabase = await createServerSupabase()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { data: job } = await supabase
    .from('ocr_jobs')
    .select('id, teacher_id')
    .eq('id', jobId)
    .eq('teacher_id', user.id)
    .single()

  if (!job) return NextResponse.json({ error: 'Job không tồn tại' }, { status: 404 })

  const body = await req.json()
  const markdown = typeof body.markdown === 'string' ? body.markdown : null
  if (markdown === null) return NextResponse.json({ error: 'markdown field required' }, { status: 400 })

  await supabase
    .from('ocr_jobs')
    .update({ normalized_markdown: markdown, updated_at: new Date().toISOString() })
    .eq('id', jobId)

  return NextResponse.json({ ok: true })
}
