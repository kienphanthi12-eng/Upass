import { NextRequest, NextResponse } from 'next/server'
import { createServerSupabase } from '@/lib/supabase-server'

export async function POST(req: NextRequest) {
  const supabase = await createServerSupabase()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  try {
    const body = await req.json()
    const { title, subject_id, year, question_count, codes } = body

    if (!title || !subject_id || !codes || codes.length === 0) {
      return NextResponse.json({ error: 'Thiếu các tham số bắt buộc' }, { status: 400 })
    }

    const draft_exam_ids: string[] = []

    for (const c of codes) {
      const codeLabel = ` — Mã đề ${c.code}`
      const { data: exam, error: examErr } = await supabase
        .from('draft_exams')
        .insert({
          teacher_id: user.id,
          title: `${title}${codeLabel}`,
          exam_type: 'offline',
          exam_year: Number(year) || new Date().getFullYear(),
          subject_id: Number(subject_id),
          status: 'draft',
        })
        .select('id')
        .single()

      if (examErr || !exam) {
        throw new Error(`Không tạo được draft exam cho mã đề ${c.code}: ${examErr?.message}`)
      }

      // Generate draft questions (Question 1 to question_count)
      const draftQuestions = []
      for (let i = 1; i <= question_count; i++) {
        const correct_ans = c.answers[i] || ''
        draftQuestions.push({
          draft_exam_id: exam.id,
          question_number: i,
          question_type: 'trac_nghiem',
          content: `Đáp án đúng câu hỏi số ${i} (Mã đề ${c.code})`,
          options: {
            A: 'Đáp án A',
            B: 'Đáp án B',
            C: 'Đáp án C',
            D: 'Đáp án D',
          },
          correct_answer: correct_ans || null,
          difficulty_level: 'Nhận biết',
        })
      }

      if (draftQuestions.length > 0) {
        const { error: qErr } = await supabase
          .from('draft_questions')
          .insert(draftQuestions)
        if (qErr) throw qErr
      }

      draft_exam_ids.push(exam.id)
    }

    return NextResponse.json({ success: true, draft_exam_ids })
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    return NextResponse.json({ error: msg }, { status: 500 })
  }
}
