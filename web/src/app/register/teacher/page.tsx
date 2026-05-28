'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase'
import { AlertCircle, CheckCircle, KeyRound } from 'lucide-react'
import AuthShell from '@/components/ui/AuthShell'
import EditorialInput from '@/components/ui/EditorialInput'
import { notify } from '@/lib/notify'

export default function TeacherRegisterPage() {
  const router = useRouter()
  const supabase = createClient()

  const [form, setForm] = useState({
    fullName: '',
    email: '',
    password: '',
    confirmPassword: '',
    inviteCode: '',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  const update = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }))

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (form.password !== form.confirmPassword) {
      setError('Mật khẩu xác nhận không khớp.')
      return
    }
    if (form.password.length < 6) {
      setError('Mật khẩu phải có ít nhất 6 ký tự.')
      return
    }

    setLoading(true)

    const checkRes = await fetch('/api/teacher/check-invite', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ inviteCode: form.inviteCode }),
    })
    const checkData = await checkRes.json()
    if (!checkData.ok) {
      setError(checkData.error || 'Mã mời không đúng.')
      setLoading(false)
      return
    }

    const { data, error: signUpErr } = await supabase.auth.signUp({
      email: form.email,
      password: form.password,
    })

    if (signUpErr) {
      setError(
        signUpErr.message.includes('already')
          ? 'Email này đã được đăng ký rồi.'
          : 'Đăng ký thất bại: ' + signUpErr.message,
      )
      setLoading(false)
      return
    }
    if (!data.user) {
      setError('Không tạo được tài khoản. Vui lòng thử lại.')
      setLoading(false)
      return
    }

    const { error: teacherErr } = await supabase.from('teachers').insert({
      id: data.user.id,
      full_name: form.fullName.trim(),
      email: form.email.trim(),
    })

    if (teacherErr) {
      setError('Lỗi tạo hồ sơ giáo viên: ' + teacherErr.message)
      setLoading(false)
      return
    }

    // Gửi thông báo Telegram
    notify({
      type: 'register',
      fullName: form.fullName.trim(),
      email: form.email.trim(),
      role: 'teacher',
    })

    setLoading(false)
    setSuccess(true)
    setTimeout(() => router.push('/teacher/dashboard'), 1500)
  }

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-paper">
        <div className="text-center max-w-sm px-6">
          <div className="w-16 h-16 rounded-full bg-moss-bg flex items-center justify-center mx-auto mb-6">
            <CheckCircle size={30} className="text-moss" />
          </div>
          <p className="font-display text-3xl text-ink mb-2">
            <em className="italic">Đăng ký</em> thành công.
          </p>
          <p className="text-sm text-ink-50">Đang vào cổng giáo viên…</p>
        </div>
      </div>
    )
  }

  return (
    <AuthShell
      sectionNumber={2}
      sectionLabel="Cổng giáo viên"
      title={<>Tạo tài khoản <em className="italic">giáo viên</em>.</>}
      subtitle="Cần mã mời từ nhà trường để đăng ký."
      footer={
        <div className="flex flex-col gap-3 text-ink-50">
          <span>
            Đã có tài khoản?{' '}
            <Link href="/teacher/login" className="text-ink link-editorial">
              Đăng nhập
            </Link>
          </span>
          <Link href="/register" className="text-ink-50 hover:text-ink link-editorial">
            Đăng ký tài khoản học sinh →
          </Link>
        </div>
      }
    >
      <form onSubmit={handleRegister} className="flex flex-col gap-6">
        {error && (
          <div className="flex items-start gap-2 p-3 bg-ember-bg border-l-2 border-ember text-ember text-sm">
            <AlertCircle size={15} className="shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {/* Mã mời — emphasized */}
        <div className="border-l-2 border-moss pl-5">
          <EditorialInput
            label={<span className="inline-flex items-center gap-1.5"><KeyRound size={11} /> Mã mời nhà trường</span>}
            required
            value={form.inviteCode}
            onChange={e => update('inviteCode', e.target.value)}
            placeholder="Nhập mã mời…"
            hint="Liên hệ quản trị viên nếu chưa có mã."
          />
        </div>

        <EditorialInput
          label="Họ và tên" required
          value={form.fullName}
          onChange={e => update('fullName', e.target.value)}
          placeholder="Nguyễn Thị B"
        />
        <EditorialInput
          label="Email" type="email" required
          value={form.email}
          onChange={e => update('email', e.target.value)}
          placeholder="giaovien@upass.edu.vn"
        />
        <EditorialInput
          label="Mật khẩu" type="password" required
          value={form.password}
          onChange={e => update('password', e.target.value)}
          placeholder="Ít nhất 6 ký tự"
        />
        <EditorialInput
          label="Xác nhận mật khẩu" type="password" required
          value={form.confirmPassword}
          onChange={e => update('confirmPassword', e.target.value)}
          placeholder="Nhập lại mật khẩu"
        />

        <button
          type="submit"
          disabled={loading}
          className="mt-4 w-full inline-flex items-center justify-center gap-2 py-4 bg-ink text-paper text-sm tracking-label hover:bg-moss transition-colors disabled:opacity-50"
        >
          {loading
            ? <span className="w-4 h-4 border border-paper/30 border-t-paper rounded-full animate-spin" />
            : null}
          {loading ? 'Đang tạo tài khoản…' : 'Đăng ký giáo viên →'}
        </button>
      </form>
    </AuthShell>
  )
}
