import { NextRequest, NextResponse } from 'next/server'

export async function POST(req: NextRequest) {
  const { inviteCode } = await req.json()
  const expected = process.env.TEACHER_INVITE_CODE || 'kimngoc2026'
  if (!inviteCode || inviteCode.trim() !== expected) {
    return NextResponse.json({ ok: false, error: 'Mã mời không đúng.' }, { status: 403 })
  }
  return NextResponse.json({ ok: true })
}
