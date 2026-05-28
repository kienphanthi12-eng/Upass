import { NextRequest, NextResponse } from 'next/server'
import { createServerSupabase } from '@/lib/supabase-server'
import { createAdminSupabase } from '@/lib/supabase-admin'

export async function GET(_req: NextRequest) {
  const supabase = await createServerSupabase()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { data: teacher } = await supabase
    .from('teachers')
    .select('id')
    .eq('id', user.id)
    .single()
  if (!teacher) return NextResponse.json({ error: 'Forbidden' }, { status: 403 })

  const admin = createAdminSupabase()
  
  // 1. Fetch all registered students
  const { data: studentsData, error: studentsError } = await admin
    .from('students')
    .select('id, full_name, class_name, student_code')

  if (studentsError) return NextResponse.json({ error: studentsError.message }, { status: 500 })

  // 2. Fetch all completed exam submissions
  const { data: submissionsData, error: subsError } = await admin
    .from('exam_submissions')
    .select('student_id, score, submitted_at')
    .eq('status', 'completed')

  if (subsError) return NextResponse.json({ error: subsError.message }, { status: 500 })

  // 3. Map submissions to student_id
  const submissionMap = new Map<string, { score: number; submitted_at: string }[]>()
  for (const sub of (submissionsData ?? [])) {
    if (!sub.student_id) continue
    const existing = submissionMap.get(sub.student_id) || []
    existing.push({ score: sub.score ?? 0, submitted_at: sub.submitted_at })
    submissionMap.set(sub.student_id, existing)
  }

  // 4. Build response array with stats
  const students = (studentsData ?? []).map(s => {
    const subs = submissionMap.get(s.id) || []
    const examCount = subs.length
    const totalScore = subs.reduce((sum, item) => sum + item.score, 0)
    const avgScore = examCount > 0 ? +(totalScore / examCount).toFixed(2) : 0
    const lastSubmittedAt = examCount > 0
      ? subs.reduce((latest, item) => item.submitted_at > latest ? item.submitted_at : latest, subs[0].submitted_at)
      : null

    return {
      student_id: s.id,
      full_name: s.full_name,
      class_name: s.class_name,
      student_code: s.student_code,
      exam_count: examCount,
      avg_score: avgScore,
      last_submitted_at: lastSubmittedAt,
    }
  })

  // 5. Sort: completed exams recently first, then non-attempted students
  students.sort((a, b) => {
    if (!a.last_submitted_at && !b.last_submitted_at) return 0
    if (!a.last_submitted_at) return 1
    if (!b.last_submitted_at) return -1
    return b.last_submitted_at.localeCompare(a.last_submitted_at)
  })

  return NextResponse.json(students)
}
