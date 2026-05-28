import { NextRequest, NextResponse } from 'next/server'
import { createServerSupabase } from '@/lib/supabase-server'

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  const supabase = await createServerSupabase()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { data, error } = await supabase
    .from('draft_exams')
    .select('*, ocr_jobs(filename, status), draft_questions(*)')
    .eq('id', id)
    .eq('teacher_id', user.id)
    .single()

  if (error || !data) return NextResponse.json({ error: 'Draft không tồn tại' }, { status: 404 })
  return NextResponse.json(data)
}
