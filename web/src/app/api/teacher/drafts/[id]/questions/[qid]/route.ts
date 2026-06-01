import { NextRequest, NextResponse } from 'next/server'
import { createServerSupabase } from '@/lib/supabase-server'

type Params = { id: string; qid: string }

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<Params> }
) {
  const { id, qid } = await params
  const supabase = await createServerSupabase()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  // Xác nhận câu hỏi thuộc draft exam của giáo viên
  const { data: q } = await supabase
    .from('draft_questions')
    .select('id, draft_exam_id')
    .eq('id', qid)
    .eq('draft_exam_id', id)
    .single()

  if (!q) return NextResponse.json({ error: 'Câu hỏi không tồn tại' }, { status: 404 })

  const body = await req.json()
  const allowed = [
    'content', 'options', 'correct_answer', 'difficulty_level', 
    'question_type', 'question_number', 'explanation', 'needs_review', 'review_reason'
  ]
  const updates: Record<string, unknown> = { updated_at: new Date().toISOString() }
  for (const key of allowed) {
    if (key in body) updates[key] = body[key]
  }

  const { error } = await supabase.from('draft_questions').update(updates).eq('id', qid)
  if (error) return NextResponse.json({ error: error.message }, { status: 500 })

  return NextResponse.json({ ok: true })
}

export async function DELETE(
  _req: NextRequest,
  { params }: { params: Promise<Params> }
) {
  const { id, qid } = await params
  const supabase = await createServerSupabase()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { error } = await supabase
    .from('draft_questions')
    .delete()
    .eq('id', qid)
    .eq('draft_exam_id', id)

  if (error) return NextResponse.json({ error: error.message }, { status: 500 })
  return NextResponse.json({ ok: true })
}
