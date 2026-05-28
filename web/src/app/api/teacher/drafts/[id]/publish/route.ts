import { NextRequest, NextResponse } from 'next/server'
import { createServerSupabase } from '@/lib/supabase-server'
import { createAdminSupabase } from '@/lib/supabase-admin'
import { pickNextCity } from '@/lib/cities'

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  const supabase = await createServerSupabase()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  // Load draft exam + questions
  const { data: draft } = await supabase
    .from('draft_exams')
    .select('*, draft_questions(*)')
    .eq('id', id)
    .eq('teacher_id', user.id)
    .single()

  if (!draft) return NextResponse.json({ error: 'Draft không tồn tại' }, { status: 404 })
  if (draft.status === 'published') {
    return NextResponse.json({ error: 'Đề này đã được publish rồi' }, { status: 400 })
  }

  const body = await req.json()
  const title = body.title || draft.title
  const examYear = body.exam_year || draft.exam_year
  const examType = body.exam_type || draft.exam_type

  try {
    // Pick a city codename — first unused one in the pool
    const { data: usedRows } = await supabase
      .from('exams')
      .select('display_title')
      .not('display_title', 'is', null)
    const usedSet = new Set<string>((usedRows ?? []).map(r => r.display_title as string))
    const city = pickNextCity(usedSet) ?? null

    // Insert vào bảng exams (production)
    const { data: newExam, error: examErr } = await supabase
      .from('exams')
      .insert({
        title,
        display_title: city,
        year: examYear,
        exam_type: examType,
        subject_id: draft.subject_id || 1,
        total_pages: null,
      })
      .select('id')
      .single()

    if (examErr || !newExam) {
      throw new Error(examErr?.message || 'Không insert được vào bảng exams')
    }

    const examId = newExam.id

    // Insert questions (production)
    const questions = (draft.draft_questions || []) as Array<{
      question_number: number | null
      question_type: string
      content: string
      options: Record<string, string> | null
      correct_answer: string | null
      difficulty_level: string
    }>

    if (questions.length > 0) {
      const questionsPayload = questions.map(q => ({
        exam_id: examId,
        subject_id: draft.subject_id || 1,
        topic_id: null,
        question_number: q.question_number ?? 0,
        content: q.content || '',
        question_type: q.question_type,
        level: q.difficulty_level,
        options: q.options,
        correct_answer: q.correct_answer,
        has_formula: /\$/.test(q.content || ''),
        has_image: /!\[/.test(q.content || ''),
      }))

      const { error: qErr } = await supabase.from('questions').insert(questionsPayload)
      if (qErr) throw new Error(qErr.message)
    }

    // Cập nhật draft → published
    await supabase
      .from('draft_exams')
      .update({ status: 'published', published_exam_id: examId, updated_at: new Date().toISOString() })
      .eq('id', id)

    return NextResponse.json({ examId, questionCount: questions.length })
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    return NextResponse.json({ error: msg }, { status: 500 })
  }
}
