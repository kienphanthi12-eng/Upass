import { NextRequest, NextResponse } from 'next/server'
import { createServerSupabase } from '@/lib/supabase-server'
import { createAdminSupabase } from '@/lib/supabase-admin'

/**
 * GET /api/teacher/issues
 * List all question reports with question + exam context.
 * Optional: ?status=open|resolved|dismissed (default 'open')
 */
export async function GET(req: NextRequest) {
  const supabase = await createServerSupabase()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { data: teacher } = await supabase
    .from('teachers').select('id').eq('id', user.id).single()
  if (!teacher) return NextResponse.json({ error: 'Forbidden' }, { status: 403 })

  const status = req.nextUrl.searchParams.get('status') ?? 'open'

  const admin = createAdminSupabase()
  const { data, error } = await admin
    .from('question_reports')
    .select(`
      id, question_id, reported_by, reporter_role, note, status, created_at, resolved_at,
      questions(id, content, question_number, exam_id, exams(id, title, display_title, year))
    `)
    .eq('status', status)
    .order('created_at', { ascending: false })
    .limit(200)

  if (error) return NextResponse.json({ error: error.message }, { status: 500 })
  return NextResponse.json(data ?? [])
}
