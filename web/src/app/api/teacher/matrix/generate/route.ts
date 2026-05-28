import { NextRequest, NextResponse } from 'next/server'
import { createServerSupabase } from '@/lib/supabase-server'
import { checkFeasibility, generateExamVariants } from '@/lib/matrix'

export const maxDuration = 120

/**
 * POST /api/teacher/matrix/generate
 * Body: {
 *   subject_id, cells, variants (1-4),
 *   title, exam_type, exam_year
 * }
 */
export async function POST(req: NextRequest) {
  const supabase = await createServerSupabase()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  // Kiểm tra role teacher
  const { data: teacher } = await supabase.from('teachers').select('id').eq('id', user.id).single()
  if (!teacher) return NextResponse.json({ error: 'Không có quyền giáo viên' }, { status: 403 })

  const body = await req.json()
  const { subject_id, cells, variants = 1, title, exam_type, exam_year } = body

  if (!subject_id || !Array.isArray(cells) || cells.length === 0) {
    return NextResponse.json({ error: 'subject_id và cells[] là bắt buộc' }, { status: 400 })
  }
  if (!title?.trim()) {
    return NextResponse.json({ error: 'Tiêu đề đề thi là bắt buộc' }, { status: 400 })
  }
  if (variants < 1 || variants > 4) {
    return NextResponse.json({ error: 'variants phải từ 1-4' }, { status: 400 })
  }

  // Feasibility check trước khi generate
  const feasibility = await checkFeasibility(supabase, { subject_id, cells })
  if (!feasibility.feasible) {
    const insufficient = feasibility.cells
      .filter(c => !c.ok)
      .map(c => `"${c.topic_name}" ${c.level}: cần ${c.required}, có ${c.available}`)
    return NextResponse.json({
      error: 'Ngân hàng câu không đủ',
      details: insufficient,
      feasibility,
    }, { status: 422 })
  }

  const result = await generateExamVariants(supabase, {
    matrix: { subject_id, cells },
    variants,
    title: title.trim(),
    exam_type: exam_type ?? 'thi_thu',
    exam_year: exam_year ?? new Date().getFullYear(),
    teacher_id: user.id,
  })

  return NextResponse.json(result)
}
