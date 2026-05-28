import { NextRequest, NextResponse } from 'next/server'
import { createServerSupabase } from '@/lib/supabase-server'
import { mineruRequestUploadUrl, mineruUploadFile } from '@/lib/mineru'
import { spawnSync } from 'child_process'
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

    // ── Xử lý file Word (.docx) hoặc LaTeX (.tex) cục bộ ────────────────────
    if (ext === 'docx' || ext === 'tex') {
      const tempPath = path.join(os.tmpdir(), `${job.id}.${ext}`)
      fs.writeFileSync(tempPath, buffer)

      const scriptPath = path.join(process.cwd(), '..', 'processor', 'parse_to_markdown.py')
      const result = spawnSync('python', [scriptPath, tempPath], { encoding: 'utf8' })

      // Xóa file tạm
      try { fs.unlinkSync(tempPath) } catch {}

      if (result.status !== 0) {
        throw new Error(result.stderr || 'Lỗi parse file python')
      }

      const markdown = result.stdout.trim()
      if (!markdown) {
        throw new Error('File không chứa nội dung hoặc rỗng')
      }

      // Lưu markdown trực tiếp và đổi status → ocr_done để client gọi normalize tiếp
      await supabase
        .from('ocr_jobs')
        .update({
          markdown,
          status: 'ocr_done',
          updated_at: new Date().toISOString(),
        })
        .eq('id', job.id)

      return NextResponse.json({ jobId: job.id })
    }

    // ── Xử lý file Excel (.xlsx) cục bộ ──────────────────────────────────────
    if (ext === 'xlsx') {
      const tempPath = path.join(os.tmpdir(), `${job.id}.xlsx`)
      fs.writeFileSync(tempPath, buffer)

      const scriptPath = path.join(process.cwd(), '..', 'processor', 'excel_parser.py')
      const result = spawnSync('python', [scriptPath, tempPath], { encoding: 'utf8' })

      // Xóa file tạm
      try { fs.unlinkSync(tempPath) } catch {}

      if (result.status !== 0) {
        throw new Error(result.stderr || 'Lỗi parse Excel python')
      }

      const parsed = JSON.parse(result.stdout)
      if (parsed.error) {
        throw new Error(parsed.error)
      }

      const examTitle = filename.replace(/\.xlsx$/i, '').replace(/[-_]/g, ' ')
      
      // Tạo draft_exam trực tiếp
      const { data: draftExam, error: examErr } = await supabase
        .from('draft_exams')
        .insert({
          teacher_id: user.id,
          ocr_job_id: job.id,
          title: examTitle,
          status: 'draft',
          exam_type: parsed.type === 'offline_answer_key' ? 'offline' : 'thi_thu'
        })
        .select('id')
        .single()

      if (examErr || !draftExam) {
        throw new Error('Không tạo được draft exam từ Excel')
      }

      // Chuẩn hóa và insert draft_questions
      const questionsData = (parsed.data || []).map((q: any) => ({
        draft_exam_id: draftExam.id,
        question_number: q.question_number,
        question_type: q.question_type || 'trac_nghiem',
        content: q.content || `Đáp án mã đề ${q.ma_de || ''}`,
        options: q.options || null,
        correct_answer: q.correct_answer || null,
        difficulty_level: q.difficulty_level || 'Nhận biết',
        topic: q.topic || null
      }))

      if (questionsData.length > 0) {
        await supabase.from('draft_questions').insert(questionsData)
      }

      // Cập nhật ocr_job trực tiếp → done
      await supabase
        .from('ocr_jobs')
        .update({
          status: 'done',
          question_count: questionsData.length,
          updated_at: new Date().toISOString(),
        })
        .eq('id', job.id)

      return NextResponse.json({ jobId: job.id })
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
