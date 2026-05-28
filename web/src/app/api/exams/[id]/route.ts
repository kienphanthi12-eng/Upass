import { NextRequest, NextResponse } from 'next/server'
import { createAdminSupabase } from '@/lib/supabase-admin'

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  const admin = createAdminSupabase()

  const { data, error } = await admin
    .from('exams')
    .select('id, title, display_title, year, exam_type')
    .eq('id', Number(id))
    .single()

  if (error || !data) return NextResponse.json({ error: 'Không tìm thấy đề' }, { status: 404 })
  return NextResponse.json(data)
}
