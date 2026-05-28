import { NextRequest, NextResponse } from 'next/server'
import { createServerSupabase } from '@/lib/supabase-server'

export async function POST(req: NextRequest) {
  const supabase = await createServerSupabase()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { data: teacher } = await supabase.from('teachers').select('id').eq('id', user.id).single()
  if (!teacher) return NextResponse.json({ error: 'Không có quyền giáo viên' }, { status: 403 })

  const body = await req.json()
  const { exam_id, assigned_to } = body

  if (!exam_id || !assigned_to) {
    return NextResponse.json({ error: 'Thiếu exam_id hoặc assigned_to' }, { status: 400 })
  }

  // Kiểm tra exam tồn tại
  const { data: exam } = await supabase.from('exams').select('id').eq('id', exam_id).single()
  if (!exam) return NextResponse.json({ error: 'Đề thi không tồn tại' }, { status: 404 })

  const { error } = await supabase
    .from('assignments')
    .upsert({ exam_id, teacher_id: user.id, assigned_to }, { onConflict: 'exam_id,teacher_id,assigned_to' })

  if (error) return NextResponse.json({ error: error.message }, { status: 500 })
  return NextResponse.json({ ok: true })
}

export async function GET(req: NextRequest) {
  const supabase = await createServerSupabase()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { searchParams } = new URL(req.url)
  const examId = searchParams.get('exam_id')

  let query = supabase
    .from('assignments')
    .select('*, exams(id, title, year, exam_type)')
    .eq('teacher_id', user.id)
    .order('created_at', { ascending: false })

  if (examId) query = query.eq('exam_id', examId)

  const { data, error } = await query
  if (error) return NextResponse.json({ error: error.message }, { status: 500 })
  return NextResponse.json(data)
}
