import { NextRequest, NextResponse } from 'next/server'
import { createServerSupabase } from '@/lib/supabase-server'
import { checkFeasibility } from '@/lib/matrix'

/**
 * POST /api/teacher/matrix/check
 * Body: { subject_id, cells: [{topic_id, topic_name, level, count}] }
 * Trả về feasibility report: ô nào đủ câu, ô nào thiếu.
 */
export async function POST(req: NextRequest) {
  const supabase = await createServerSupabase()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const body = await req.json()
  const { subject_id, cells } = body

  if (!subject_id || !Array.isArray(cells)) {
    return NextResponse.json({ error: 'subject_id và cells[] là bắt buộc' }, { status: 400 })
  }

  const result = await checkFeasibility(supabase, { subject_id, cells })
  return NextResponse.json(result)
}
