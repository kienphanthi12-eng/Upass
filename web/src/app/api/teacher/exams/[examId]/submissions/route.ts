import { NextRequest, NextResponse } from 'next/server'
import { createServerSupabase } from '@/lib/supabase-server'
import { createAdminSupabase } from '@/lib/supabase-admin'

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ examId: string }> }
) {
  const { examId } = await params
  const supabase = await createServerSupabase()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  // Kiểm tra giáo viên có quyền xem đề này không (phải là người publish)
  const { data: draft } = await supabase
    .from('draft_exams')
    .select('id')
    .eq('published_exam_id', Number(examId))
    .eq('teacher_id', user.id)
    .single()

  if (!draft) return NextResponse.json({ error: 'Không có quyền xem' }, { status: 403 })

  const admin = createAdminSupabase()
  const { data, error } = await admin
    .from('exam_submissions')
    .select('id, student_id, submitted_at, time_taken, score, total_questions, correct_count, status, students(full_name, class_name, student_code)')
    .eq('exam_id', Number(examId))
    .eq('status', 'completed')
    .order('submitted_at', { ascending: false })

  if (error) return NextResponse.json({ error: error.message }, { status: 500 })
  return NextResponse.json(data ?? [])
}
