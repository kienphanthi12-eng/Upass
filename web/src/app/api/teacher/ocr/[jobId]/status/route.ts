import { NextRequest, NextResponse } from 'next/server'
import { createServerSupabase } from '@/lib/supabase-server'
import { mineruPollBatch, mineruDownloadMarkdown } from '@/lib/mineru'

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
    .select('*')
    .eq('id', jobId)
    .eq('teacher_id', user.id)
    .single()

  if (!job) return NextResponse.json({ error: 'Job không tồn tại' }, { status: 404 })

  // Nếu đang chờ MinerU → poll lấy trạng thái mới
  if (job.status === 'ocr_running' && job.mineru_batch_id) {
    try {
      const poll = await mineruPollBatch(job.mineru_batch_id)

      if (poll.done && poll.result) {
        // Download markdown + ảnh từ ZIP
        const { markdown: rawMarkdown, images } = await mineruDownloadMarkdown(poll.result)

        // Upload ảnh lên Supabase Storage (public bucket ocr-images)
        let markdown = rawMarkdown
        const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
        for (const [filename, bytes] of images) {
          const storagePath = `${job.id}/${filename}`
          const { error: uploadErr } = await supabase.storage
            .from('ocr-images')
            .upload(storagePath, bytes, {
              contentType: filename.match(/\.png$/i) ? 'image/png'
                : filename.match(/\.gif$/i) ? 'image/gif'
                : filename.match(/\.webp$/i) ? 'image/webp'
                : 'image/jpeg',
              upsert: true,
            })
          if (!uploadErr) {
            // Thay path tương đối → URL public Supabase
            const publicUrl = `${supabaseUrl}/storage/v1/object/public/ocr-images/${storagePath}`
            // Replace cả images/filename lẫn chỉ filename trong markdown
            markdown = markdown
              .replaceAll(`images/${filename}`, publicUrl)
              .replaceAll(`(${filename})`, `(${publicUrl})`)
          }
        }

        await supabase
          .from('ocr_jobs')
          .update({
            status: 'ocr_done',
            markdown,
            mineru_result: poll.result,
            updated_at: new Date().toISOString(),
          })
          .eq('id', jobId)

        return NextResponse.json({ status: 'ocr_done', markdownLength: markdown.length })
      }

      if (poll.done && poll.error) {
        await supabase
          .from('ocr_jobs')
          .update({ status: 'error', error_msg: poll.error, updated_at: new Date().toISOString() })
          .eq('id', jobId)
        return NextResponse.json({ status: 'error', error: poll.error })
      }

      return NextResponse.json({ status: 'ocr_running', state: poll.state })
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      return NextResponse.json({ status: job.status, state: msg })
    }
  }

  return NextResponse.json({
    status: job.status,
    questionCount: job.question_count,
    errorMsg: job.error_msg,
  })
}
