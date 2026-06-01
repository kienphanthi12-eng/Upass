import { NextRequest, NextResponse } from 'next/server'
import { createServerSupabase } from '@/lib/supabase-server'
import { mineruRequestUploadUrl, mineruUploadFile } from '@/lib/mineru'
import { spawn, execSync } from 'child_process'
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

    // Save uploaded file to temp path to run local python parser checks
    const tempPath = path.join(os.tmpdir(), `${job.id}.${ext}`)
    fs.writeFileSync(tempPath, buffer)

    let routeToAzota = false
    let detectedSubject = (formData.get('subject') as string) || ''
    
    // Perform Azota formatting check for docx/pdf if requested or checking for auto-route
    if (['docx', 'pdf'].includes(ext)) {
      try {
        const detectScript = path.join(process.cwd(), '..', 'processor', 'detect_azota.py')
        const detectResult = execSync(`python "${detectScript}" "${tempPath}"`, { encoding: 'utf8' })
        const check = JSON.parse(detectResult.trim())
        
        // Chỉ tự động chuyển sang Azota nếu:
        // 1. Giáo viên chủ động chọn nhập đề Azota (importType === 'azota')
        // 2. Hoặc đó là file Word .docx đúng định dạng Azota (vì .docx dịch trực tiếp tốt hơn)
        // KHÔNG tự động chuyển PDF sang Azota PDF parser ở tab OCR thường vì đó là parser text-only (không trích xuất ảnh/bảng biểu như MinerU).
        const isAzotaDocx = (ext === 'docx' && check.is_azota)
        if (importType === 'azota' || isAzotaDocx) {
          routeToAzota = true
          if (!detectedSubject || detectedSubject === '') {
            detectedSubject = check.subject !== 'UNKNOWN' ? check.subject : 'TOAN'
          }
        }
      } catch (err) {
        console.error('Format detection failed:', err)
        // If explicitly requested as azota, we still try to route it
        if (importType === 'azota') {
          routeToAzota = true
          if (!detectedSubject) detectedSubject = 'TOAN'
        }
      }
    }

    // ── ROUTE 1: Azota pipeline (Direct parse via Python) ───────────────────
    if (routeToAzota) {
      const scriptPath = path.join(process.cwd(), '..', 'processor', 'azota_job.py')
      const child = spawn('python', [
        scriptPath,
        '--file_path', tempPath,
        '--job_id', job.id,
        '--user_id', user.id,
        '--filename', filename,
        '--subject', detectedSubject,
        '--kind', ext
      ], {
        detached: true,
        stdio: 'ignore'
      })
      child.unref()

      await supabase
        .from('ocr_jobs')
        .update({
          status: 'ocr_running',
          updated_at: new Date().toISOString(),
        })
        .eq('id', job.id)

      return NextResponse.json({ jobId: job.id })
    }

    // ── ROUTE 2: MinerU OCR Pipeline (Fallback / Default) ───────────────────
    let mineruFileBuffer: ArrayBuffer = fileBuffer
    let mineruFilename = filename
    let mineruExt = ext
    let pdfTempPath: string | null = null

    // For non-Azota docx: Convert to PDF first, then upload to MinerU
    if (ext === 'docx') {
      try {
        const convertScript = path.join(process.cwd(), '..', 'convert_docx_to_pdf.py')
        pdfTempPath = path.join(os.tmpdir(), `${job.id}.pdf`)
        execSync(`python "${convertScript}" "${tempPath}" "${pdfTempPath}"`, { encoding: 'utf8' })
        
        if (fs.existsSync(pdfTempPath)) {
          const buf = fs.readFileSync(pdfTempPath)
          mineruFileBuffer = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength)
          mineruFilename = filename.replace(/\.docx$/i, '.pdf')
          mineruExt = 'pdf'
        } else {
          throw new Error('PDF conversion failed')
        }
      } catch (err) {
        // Clean up temp files
        try { fs.unlinkSync(tempPath) } catch {}
        throw new Error('Không thể chuyển đổi Word sang PDF. Vui lòng tự lưu PDF rồi tải lại.')
      }
    }

    // Process PDF and images via MinerU
    if (mineruExt === 'pdf' || ['png', 'jpg', 'jpeg'].includes(mineruExt)) {
      // Step 1: Request upload URL from MinerU
      const { batchId, uploadUrl } = await mineruRequestUploadUrl(mineruFilename)

      // Step 2: Upload file bytes to OSS
      await mineruUploadFile(uploadUrl, mineruFileBuffer)

      // Step 3: Save PDF to Supabase Storage
      let pdfStoragePath: string | null = null
      if (mineruExt === 'pdf') {
        try {
          const storagePath = `${user.id}/${job.id}.pdf`
          const { error: storageErr } = await supabase.storage
            .from('teacher-pdfs')
            .upload(storagePath, mineruFileBuffer, { contentType: 'application/pdf', upsert: false })
          if (!storageErr) pdfStoragePath = storagePath
        } catch { /* storage failure is non-critical */ }
      }

      // Update job with batch_id and status -> ocr_running
      await supabase
        .from('ocr_jobs')
        .update({
          mineru_batch_id: batchId,
          status: 'ocr_running',
          pdf_storage_path: pdfStoragePath,
          updated_at: new Date().toISOString(),
        })
        .eq('id', job.id)

      // Clean up temp files
      try { fs.unlinkSync(tempPath) } catch {}
      if (pdfTempPath && fs.existsSync(pdfTempPath)) {
        try { fs.unlinkSync(pdfTempPath) } catch {}
      }

      return NextResponse.json({ jobId: job.id })
    }

    // Clean up temp file
    try { fs.unlinkSync(tempPath) } catch {}

    // Other non-supported formats
    if (['tex', 'xlsx', 'zip'].includes(ext)) {
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
