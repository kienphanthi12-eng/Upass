import { NextRequest, NextResponse } from 'next/server'
import { createServerSupabase } from '@/lib/supabase-server'

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  const supabase = await createServerSupabase()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { data: draft } = await supabase
    .from('draft_exams')
    .select('id')
    .eq('id', id)
    .eq('teacher_id', user.id)
    .single()

  if (!draft) return NextResponse.json({ error: 'Draft không tồn tại' }, { status: 404 })

  const body = await req.json()
  const { data: question, error } = await supabase
    .from('draft_questions')
    .insert({
      draft_exam_id: id,
      question_type: body.question_type ?? 'trac_nghiem',
      content: body.content ?? '',
      options: body.options ?? null,
      correct_answer: body.correct_answer ?? null,
      difficulty_level: body.difficulty_level ?? 'Nhận biết',
      question_number: body.question_number ?? null,
    })
    .select('*')
    .single()

  if (error) return NextResponse.json({ error: error.message }, { status: 500 })
  return NextResponse.json(question, { status: 201 })
}
