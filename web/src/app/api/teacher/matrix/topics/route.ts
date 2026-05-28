import { NextRequest, NextResponse } from 'next/server'
import { createServerSupabase } from '@/lib/supabase-server'

/**
 * GET /api/teacher/matrix/topics?subject_id=1
 * Trả về danh sách topics theo subject kèm số câu hỏi có sẵn theo từng mức độ.
 */
export async function GET(req: NextRequest) {
  const supabase = await createServerSupabase()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const subjectId = req.nextUrl.searchParams.get('subject_id')
  if (!subjectId) return NextResponse.json({ error: 'subject_id required' }, { status: 400 })

  const sid = parseInt(subjectId)

  // Lấy danh sách topics của môn
  const { data: topics } = await supabase
    .from('topics')
    .select('id, name, parent_id')
    .eq('subject_id', sid)
    .order('name')

  if (!topics || topics.length === 0) {
    return NextResponse.json({ topics: [], subject_stats: [] })
  }

  // Đếm câu hỏi theo (topic_id, level)
  const LEVELS = ['Nhận biết', 'Thông hiểu', 'Vận dụng', 'Vận dụng cao']

  // Lấy count từ DB một lần cho toàn bộ subject, group by topic + level
  const { data: counts } = await supabase
    .from('questions')
    .select('topic_id, level')
    .eq('subject_id', sid)
    .not('correct_answer', 'is', null)

  // Build count map: topic_id → level → count
  const countMap = new Map<string, number>()
  for (const row of counts ?? []) {
    const key = `${row.topic_id ?? 'null'}__${row.level}`
    countMap.set(key, (countMap.get(key) ?? 0) + 1)
  }

  // Lấy thêm thống kê toàn môn (topic_id = null)
  const subjectStats = LEVELS.map(level => ({
    level,
    count: (counts ?? []).filter(r => r.level === level).length,
  }))

  // Kết hợp topics với số câu
  const topicsWithStats = topics.map(topic => ({
    id:        topic.id,
    name:      topic.name,
    parent_id: topic.parent_id,
    levels:    LEVELS.map(level => ({
      level,
      count: countMap.get(`${topic.id}__${level}`) ?? 0,
    })),
    total: LEVELS.reduce((s, level) => s + (countMap.get(`${topic.id}__${level}`) ?? 0), 0),
  }))

  return NextResponse.json({
    topics:       topicsWithStats,
    subject_stats: subjectStats,
  })
}
