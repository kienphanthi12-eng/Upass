import { NextRequest, NextResponse } from 'next/server'
import { createServerSupabase } from '@/lib/supabase-server'
import { createAdminSupabase } from '@/lib/supabase-admin'

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ studentId: string }> }
) {
  const { studentId } = await params
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
  
  // 1. Lấy thông tin học sinh
  const { data: student, error: studentErr } = await admin
    .from('students')
    .select('id, full_name, class_name, student_code, created_at')
    .eq('id', studentId)
    .single()

  if (studentErr) {
    return NextResponse.json({ error: 'Không tìm thấy học sinh' }, { status: 404 })
  }

  // 2. Lấy toàn bộ bài thi học sinh đã làm hoặc đang làm
  const { data: submissions, error: subsErr } = await admin
    .from('exam_submissions')
    .select('id, exam_id, submitted_at, time_taken, score, total_questions, correct_count, status, exams(title, display_title, year, exam_type)')
    .eq('student_id', studentId)
    .order('submitted_at', { ascending: false })

  if (subsErr) {
    return NextResponse.json({ error: subsErr.message }, { status: 500 })
  }

  return NextResponse.json({
    student,
    submissions: submissions ?? []
  })
}
