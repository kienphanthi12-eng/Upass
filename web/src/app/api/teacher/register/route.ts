import { NextRequest, NextResponse } from 'next/server'
import { createAdminSupabase } from '@/lib/supabase-admin'

export async function POST(req: NextRequest) {
  const { fullName, email, password, inviteCode } = await req.json()

  // Kiểm tra mã mời
  const expected = process.env.TEACHER_INVITE_CODE || 'kimngoc2026'
  if (!inviteCode || inviteCode.trim() !== expected) {
    return NextResponse.json({ error: 'Mã mời không đúng.' }, { status: 403 })
  }

  if (!fullName?.trim() || !email?.trim() || !password) {
    return NextResponse.json({ error: 'Vui lòng điền đầy đủ thông tin.' }, { status: 400 })
  }
  if (password.length < 6) {
    return NextResponse.json({ error: 'Mật khẩu phải có ít nhất 6 ký tự.' }, { status: 400 })
  }

  const admin = createAdminSupabase()

  // Tạo user trong Supabase Auth
  const { data: authData, error: authErr } = await admin.auth.admin.createUser({
    email: email.trim(),
    password,
    email_confirm: true, // bỏ qua bước xác nhận email
  })

  if (authErr) {
    const msg = authErr.message.includes('already been registered') || authErr.message.includes('already exists')
      ? 'Email này đã được đăng ký rồi.'
      : authErr.message
    return NextResponse.json({ error: msg }, { status: 400 })
  }

  if (!authData.user) {
    return NextResponse.json({ error: 'Không tạo được tài khoản.' }, { status: 500 })
  }

  // Tạo record trong bảng teachers
  const { error: teacherErr } = await admin.from('teachers').insert({
    id: authData.user.id,
    full_name: fullName.trim(),
    email: email.trim(),
  })

  if (teacherErr) {
    // Rollback: xóa user vừa tạo
    await admin.auth.admin.deleteUser(authData.user.id)
    return NextResponse.json({ error: 'Lỗi tạo tài khoản giáo viên: ' + teacherErr.message }, { status: 500 })
  }

  return NextResponse.json({ ok: true })
}
