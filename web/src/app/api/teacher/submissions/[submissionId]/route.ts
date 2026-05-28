import { NextRequest, NextResponse } from 'next/server'
import { createServerSupabase } from '@/lib/supabase-server'
import { createAdminSupabase } from '@/lib/supabase-admin'

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ submissionId: string }> }
) {
  const { submissionId } = await params
  const supabase = await createServerSupabase()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  // Kiểm tra giáo viên có quyền xem không
  const { data: teacher } = await supabase
    .from('teachers')
    .select('id')
    .eq('id', user.id)
    .single()
  if (!teacher) return NextResponse.json({ error: 'Forbidden' }, { status: 403 })

  const admin = createAdminSupabase()

  // 1. Lấy thông tin chi tiết bài nộp
  const { data: submission, error: subErr } = await admin
    .from('exam_submissions')
    .select(`
      id,
      student_id,
      exam_id,
      submitted_at,
      time_taken,
      score,
      total_questions,
      correct_count,
      status,
      exams (
        id,
        title,
        display_title,
        year,
        exam_type
      ),
      students (
        id,
        full_name,
        class_name,
        student_code
      )
    `)
    .eq('id', submissionId)
    .single()

  if (subErr || !submission) {
    return NextResponse.json({ error: 'Không tìm thấy bài làm' }, { status: 404 })
  }

  // 2. Lấy toàn bộ câu hỏi của đề thi tương ứng
  const { data: questions, error: qErr } = await admin
    .from('questions')
    .select('id, exam_id, subject_id, topic_id, question_number, content, question_type, level, options, correct_answer, has_formula, has_image')
    .eq('exam_id', submission.exam_id)
    .eq('is_hidden', false)
    .order('question_number')

  if (qErr) {
    return NextResponse.json({ error: qErr.message }, { status: 500 })
  }

  // 3. Lấy câu trả lời học sinh đã chọn
  const { data: studentAnswers, error: aErr } = await admin
    .from('student_answers')
    .select('question_id, answer, is_correct')
    .eq('submission_id', submissionId)

  if (aErr) {
    return NextResponse.json({ error: aErr.message }, { status: 500 })
  }

  // Chuyển danh sách câu trả lời thành map key-value [question_id]: { answer, is_correct }
  const answersMap: Record<number, { answer: string | null; is_correct: boolean | null }> = {}
  for (const ans of (studentAnswers ?? [])) {
    answersMap[ans.question_id] = {
      answer: ans.answer,
      is_correct: ans.is_correct
    }
  }

  return NextResponse.json({
    submission,
    questions: questions ?? [],
    answers: answersMap
  })
}
