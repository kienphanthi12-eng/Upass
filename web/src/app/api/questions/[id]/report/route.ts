import { NextRequest, NextResponse } from 'next/server'
import { createServerSupabase } from '@/lib/supabase-server'
import { createAdminSupabase } from '@/lib/supabase-admin'

/**
 * POST /api/questions/[id]/report
 * Body: { note: string }
 * Any authenticated user (student or teacher) can flag a question with a note.
 * Falls back to guest if not authenticated.
 */
export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  const questionId = Number(id)
  if (!Number.isFinite(questionId)) {
    return NextResponse.json({ error: 'Question ID không hợp lệ' }, { status: 400 })
  }

  const body = await req.json().catch(() => ({}))
  const note = (body?.note ?? '').toString().trim()
  if (!note || note.length < 3) {
    return NextResponse.json({ error: 'Ghi chú phải có ít nhất 3 ký tự' }, { status: 400 })
  }
  if (note.length > 1000) {
    return NextResponse.json({ error: 'Ghi chú quá dài (tối đa 1000 ký tự)' }, { status: 400 })
  }

  const supabase = await createServerSupabase()
  const { data: { user } } = await supabase.auth.getUser()

  // Determine reporter role
  let role: 'student' | 'teacher' | 'guest' = 'guest'
  if (user) {
    const { data: teacher } = await supabase
      .from('teachers').select('id').eq('id', user.id).single()
    role = teacher ? 'teacher' : 'student'
  }

  // Use admin for the insert so guests work + bypass RLS edge cases
  const admin = createAdminSupabase()
  const { data, error } = await admin
    .from('question_reports')
    .insert({
      question_id: questionId,
      reported_by: user?.id ?? null,
      reporter_role: role,
      note,
    })
    .select('id, created_at')
    .single()

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }
  return NextResponse.json({ ok: true, id: data.id })
}
