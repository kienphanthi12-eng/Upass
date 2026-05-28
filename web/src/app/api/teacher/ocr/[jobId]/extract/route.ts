import { NextRequest, NextResponse } from 'next/server'
import { createServerSupabase } from '@/lib/supabase-server'
import { normalizeMarkdown, splitNormalizedText, extractQuestions } from '@/lib/deepseek'

export const maxDuration = 300 // 5 phút (Next.js 16)

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
    .select('*')
    .eq('id', jobId)
    .eq('teacher_id', user.id)
    .single()

  if (!job) return NextResponse.json({ error: 'Job không tồn tại' }, { status: 404 })
  if (!job.markdown && !job.normalized_markdown) {
    return NextResponse.json({ error: 'Chưa có markdown (chờ OCR xong)' }, { status: 400 })
  }

  try {
    // Bước 1: Chuẩn hóa markdown (bỏ qua nếu đã có normalized_markdown)
    let normalizedMd = job.normalized_markdown
    if (!normalizedMd) {
      await supabase.from('ocr_jobs').update({ status: 'normalizing', updated_at: new Date().toISOString() }).eq('id', jobId)
      normalizedMd = await normalizeMarkdown(job.markdown!)

      await supabase.from('ocr_jobs').update({
        normalized_markdown: normalizedMd,
        status: 'extracting',
        updated_at: new Date().toISOString(),
      }).eq('id', jobId)
    } else {
      await supabase.from('ocr_jobs')
        .update({ status: 'extracting', updated_at: new Date().toISOString() })
        .eq('id', jobId)
    }

    // Bước 2: Tách câu hỏi
    const rawQuestions = splitNormalizedText(normalizedMd!)
    if (rawQuestions.length === 0) {
      await supabase.from('ocr_jobs').update({ status: 'error', error_msg: 'Không tìm thấy câu hỏi nào', updated_at: new Date().toISOString() }).eq('id', jobId)
      return NextResponse.json({ error: 'Không tìm thấy câu hỏi nào trong file' }, { status: 400 })
    }

    // Bước 3: Dọn draft_exam cũ (nếu có) rồi tạo mới — tránh duplicate khi retry
    const { data: existing } = await supabase
      .from('draft_exams')
      .select('id')
      .eq('ocr_job_id', jobId)
      .eq('status', 'draft')
      .maybeSingle()
    if (existing) {
      await supabase.from('draft_questions').delete().eq('draft_exam_id', existing.id)
      await supabase.from('draft_exams').delete().eq('id', existing.id)
    }

    const { data: draftExam, error: examErr } = await supabase
      .from('draft_exams')
      .insert({
        teacher_id: user.id,
        ocr_job_id: jobId,
        title: job.filename.replace(/\.pdf$/i, '').replace(/[-_]/g, ' '),
        status: 'draft',
      })
      .select('id')
      .single()

    if (examErr || !draftExam) {
      throw new Error('Không tạo được draft exam')
    }

    // Bước 4: DeepSeek trích xuất JSON từng câu
    const extractedQuestions = await extractQuestions(rawQuestions, draftExam.id)

    // Bước 5: Insert draft_questions
    if (extractedQuestions.length === 0) {
      // Xóa draft_exam rỗng vừa tạo, báo lỗi
      await supabase.from('draft_exams').delete().eq('id', draftExam.id)
      await supabase.from('ocr_jobs').update({
        status: 'error',
        error_msg: 'DeepSeek không trích xuất được câu hỏi nào. Hãy kiểm tra lại nội dung markdown rồi thử lại.',
        updated_at: new Date().toISOString(),
      }).eq('id', jobId)
      return NextResponse.json({ error: 'Không trích xuất được câu hỏi nào' }, { status: 400 })
    }

    await supabase.from('draft_questions').insert(extractedQuestions)

    // Cập nhật job → done
    await supabase.from('ocr_jobs').update({
      status: 'done',
      question_count: extractedQuestions.length,
      updated_at: new Date().toISOString(),
    }).eq('id', jobId)

    return NextResponse.json({ draftExamId: draftExam.id, questionCount: extractedQuestions.length })
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    await supabase.from('ocr_jobs').update({ status: 'error', error_msg: msg, updated_at: new Date().toISOString() }).eq('id', jobId)
    return NextResponse.json({ error: msg }, { status: 500 })
  }
}
