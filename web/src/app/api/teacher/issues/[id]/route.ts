import { NextRequest, NextResponse } from 'next/server'
import { createServerSupabase } from '@/lib/supabase-server'
import { createAdminSupabase } from '@/lib/supabase-admin'

/**
 * PATCH /api/teacher/issues/[id]
 * Body: { status: 'resolved' | 'dismissed' | 'open' }
 * Teacher marks an issue as resolved/dismissed/reopens.
 */
export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  const reportId = Number(id)
  if (!Number.isFinite(reportId)) {
    return NextResponse.json({ error: 'Report ID không hợp lệ' }, { status: 400 })
  }

  const supabase = await createServerSupabase()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { data: teacher } = await supabase
    .from('teachers').select('id').eq('id', user.id).single()
  if (!teacher) return NextResponse.json({ error: 'Forbidden' }, { status: 403 })

  const body = await req.json().catch(() => ({}))
  const newStatus = body?.status
  if (!['open', 'resolved', 'dismissed'].includes(newStatus)) {
    return NextResponse.json({ error: 'Status không hợp lệ' }, { status: 400 })
  }

  const admin = createAdminSupabase()
  const { error } = await admin
    .from('question_reports')
    .update({
      status: newStatus,
      resolved_at: newStatus === 'open' ? null : new Date().toISOString(),
      resolved_by: newStatus === 'open' ? null : user.id,
    })
    .eq('id', reportId)

  if (error) return NextResponse.json({ error: error.message }, { status: 500 })
  return NextResponse.json({ ok: true })
}
