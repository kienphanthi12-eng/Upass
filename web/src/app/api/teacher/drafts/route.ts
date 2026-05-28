import { NextResponse } from 'next/server'
import { createServerSupabase } from '@/lib/supabase-server'

export async function GET() {
  const supabase = await createServerSupabase()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { data, error } = await supabase
    .from('draft_exams')
    .select('*, ocr_jobs(filename, status), draft_questions(*), exams(display_title)')
    .eq('teacher_id', user.id)
    .order('created_at', { ascending: false })

  if (error) return NextResponse.json({ error: error.message }, { status: 500 })
  return NextResponse.json(data)
}

export async function POST() {
  const supabase = await createServerSupabase()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { data: draft, error } = await supabase
    .from('draft_exams')
    .insert({
      teacher_id: user.id,
      title: 'Đề tự soạn mới',
      status: 'draft',
      exam_type: 'thi_thu',
      exam_year: new Date().getFullYear(),
      subject_id: 1,
    })
    .select('id')
    .single()

  if (error || !draft) {
    return NextResponse.json({ error: error?.message || 'Không tạo được đề mới' }, { status: 500 })
  }

  return NextResponse.json({ id: draft.id })
}
