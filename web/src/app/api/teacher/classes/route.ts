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
  
  // 1. Fetch all registered students to map class sizes
  const { data: students, error: studentsError } = await admin
    .from('students')
    .select('id, class_name')

  if (studentsError) return NextResponse.json({ error: studentsError.message }, { status: 500 })

  // 2. Fetch all completed exam submissions
  const { data: submissions, error: subsError } = await admin
    .from('exam_submissions')
    .select('student_id, score, submitted_at')
    .eq('status', 'completed')

  if (subsError) return NextResponse.json({ error: subsError.message }, { status: 500 })

  // Map student to their class, and track unique students per class
  const studentClassMap = new Map<string, string>() // student_id -> class_name
  const classStudentSetMap = new Map<string, Set<string>>() // class_name -> set of registered student_ids
  
  for (const s of (students ?? [])) {
    const cn = s.class_name?.trim() || 'Chưa phân lớp'
    studentClassMap.set(s.id, cn)
    
    const set = classStudentSetMap.get(cn) || new Set<string>()
    set.add(s.id)
    classStudentSetMap.set(cn, set)
  }

  // Statistics map for each class
  const classStatsMap = new Map<string, {
    class_name: string
    total_score: number
    submission_count: number
    last_submitted_at: string
  }>()

  // Pre-populate with all classes that have registered students
  for (const className of classStudentSetMap.keys()) {
    classStatsMap.set(className, {
      class_name: className,
      total_score: 0,
      submission_count: 0,
      last_submitted_at: '',
    })
  }

  // Aggregate submissions by class
  for (const sub of (submissions ?? [])) {
    if (!sub.student_id) continue
    const cn = studentClassMap.get(sub.student_id) || 'Chưa phân lớp'
    
    if (!classStatsMap.has(cn)) {
      classStatsMap.set(cn, {
        class_name: cn,
        total_score: 0,
        submission_count: 0,
        last_submitted_at: '',
      })
    }

    const stats = classStatsMap.get(cn)!
    stats.total_score += sub.score ?? 0
    stats.submission_count++
    if (sub.submitted_at && sub.submitted_at > stats.last_submitted_at) {
      stats.last_submitted_at = sub.submitted_at
    }
  }

  // Format final class array
  const classes = Array.from(classStatsMap.values())
    .map(c => {
      const registeredCount = classStudentSetMap.get(c.class_name)?.size || 0
      return {
        class_name: c.class_name,
        student_count: registeredCount,
        submission_count: c.submission_count,
        avg_score: c.submission_count > 0 ? +(c.total_score / c.submission_count).toFixed(2) : 0,
        last_submitted_at: c.last_submitted_at || null,
      }
    })
    .sort((a, b) => a.class_name.localeCompare(b.class_name, 'vi'))

  return NextResponse.json(classes)
}
