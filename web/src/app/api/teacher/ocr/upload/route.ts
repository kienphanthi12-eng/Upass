import { NextRequest, NextResponse } from 'next/server'
import { createServerSupabase } from '@/lib/supabase-server'
import { mineruRequestUploadUrl, mineruUploadFile } from '@/lib/mineru'
import { spawn } from 'child_process'
import * as fs from 'fs'
import * as path from 'path'
import * as os from 'os'

export async function POST(req: NextRequest) {
  const supabase = await createServerSupabase()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  // Kiểm tra role teacher
  const { data: teacher } = await supabase.from('teachers').select('id').eq('id', user.id).single()
  if (!teacher) return NextResponse.json({ error: 'Không có quyền giáo viên' }, { status: 403 })

  const formData = await req.formData()
  const importType = (formData.get('import_type') as string) || 'text'
  
  // Support both 'pdf' or any other field name
  const file = (formData.get('pdf') || formData.get('file')) as File | null
  if (!file) {
    return NextResponse.json({ error: 'Vui lòng chọn file tải lên' }, { status: 400 })
  }

  const filename = file.name
  const ext = filename.split('.').pop()?.toLowerCase()
  if (!ext || !['pdf', 'docx', 'xlsx', 'tex', 'zip', 'png', 'jpg', 'jpeg'].includes(ext)) {
    return NextResponse.json({ error: 'Định dạng file không hỗ trợ' }, { status: 400 })
  }

  // Tạo ocr_job record ban đầu
  const { data: job, error: jobErr } = await supabase
    .from('ocr_jobs')
    .insert({ teacher_id: user.id, filename, status: 'uploading' })
    .select('id')
    .single()

  if (jobErr || !job) {
    return NextResponse.json({ error: 'Không tạo được job' }, { status: 500 })
  }

  try {
    const fileBuffer = await file.arrayBuffer()
    const buffer = Buffer.from(fileBuffer)

    // ── Xử lý "Tải đề PDF 2" (Cắt câu dạng ảnh) ──────────────────────────────
    if (importType === 'pdf2' && ext === 'pdf') {
      const tempPath = path.join(os.tmpdir(), `${job.id}.pdf`)
      fs.writeFileSync(tempPath, buffer)

      const scriptPath = path.join(process.cwd(), '..', 'processor', 'crop_pdf_job.py')
      const child = spawn('python', [
        scriptPath,
        '--pdf_path', tempPath,
        '--job_id', job.id,
        '--user_id', user.id,
        '--filename', filename
      ], {
        detached: true,
        stdio: 'ignore'
      })
      child.unref()

      // Đổi trạng thái ocr_jobs → ocr_running để client bắt đầu poll
      await supabase
        .from('ocr_jobs')
        .update({
          status: 'ocr_running',
          updated_at: new Date().toISOString(),
        })
        .eq('id', job.id)

      return NextResponse.json({ jobId: job.id })
    }

    // ── Xử lý file PDF & Ảnh qua MinerU (OCR pipeline cũ) ────────────────────
    if (ext === 'pdf' || ['png', 'jpg', 'jpeg'].includes(ext)) {
      // Step 1: Lấy upload URL từ MinerU
      const { batchId, uploadUrl } = await mineruRequestUploadUrl(filename)

      // Step 2: Upload file bytes lên OSS
      await mineruUploadFile(uploadUrl, fileBuffer)

      // Step 3: Lưu PDF vào Supabase Storage
      let pdfStoragePath: string | null = null
      if (ext === 'pdf') {
        try {
          const storagePath = `${user.id}/${job.id}.pdf`
          const { error: storageErr } = await supabase.storage
            .from('teacher-pdfs')
            .upload(storagePath, fileBuffer, { contentType: 'application/pdf', upsert: false })
          if (!storageErr) pdfStoragePath = storagePath
        } catch { /* storage failure is non-critical */ }
      }

      // Cập nhật job với batch_id, đổi status → ocr_running
      await supabase
        .from('ocr_jobs')
        .update({
          mineru_batch_id: batchId,
          status: 'ocr_running',
          pdf_storage_path: pdfStoragePath,
          updated_at: new Date().toISOString(),
        })
        .eq('id', job.id)

      return NextResponse.json({ jobId: job.id })
    }

    // ── DOCX / TEX / XLSX / ZIP — không hỗ trợ trên server ──────────────────
    // (Cần Python + processor/ script, chỉ chạy được trên máy local)
    if (['docx', 'tex', 'xlsx', 'zip'].includes(ext)) {
      await supabase.from('ocr_jobs').delete().eq('id', job.id)
      return NextResponse.json(
        { error: `Định dạng .${ext} chưa được hỗ trợ trên server. Vui lòng chuyển sang PDF rồi tải lại.` },
        { status: 400 }
      )
    }

    throw new Error('Không thể xử lý định dạng file này')
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    await supabase
      .from('ocr_jobs')
      .update({ status: 'error', error_msg: msg, updated_at: new Date().toISOString() })
      .eq('id', job.id)
    return NextResponse.json({ error: msg }, { status: 500 })
  }
}
