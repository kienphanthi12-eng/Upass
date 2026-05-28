'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase'
import { AlertCircle, CheckCircle } from 'lucide-react'
import AuthShell from '@/components/ui/AuthShell'
import EditorialInput from '@/components/ui/EditorialInput'
import { notify } from '@/lib/notify'

export default function RegisterPage() {
  const router = useRouter()
  const supabase = createClient()
  const [form, setForm] = useState({
    fullName: '',
    className: '',
    studentCode: '',
    email: '',
    password: '',
    confirmPassword: '',
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

    const { data, error: signUpErr } = await supabase.auth.signUp({
      email: form.email,
      password: form.password,
    })

    if (signUpErr) {
      setLoading(false)
      setError(signUpErr.message.includes('already registered')
        ? 'Email này đã được đăng ký. Vui lòng đăng nhập.'
        : 'Đăng ký thất bại. Vui lòng thử lại.')
      return
    }

    if (data.user) {
      await supabase.from('students').insert({
        id: data.user.id,
        full_name: form.fullName,
        class_name: form.className || null,
        student_code: form.studentCode || null,
      })

      // Gửi thông báo Telegram
      notify({
        type: 'register',
        fullName: form.fullName,
        className: form.className || undefined,
        email: form.email,
        role: 'student',
      })
    }

    setLoading(false)
    setSuccess(true)
    setTimeout(() => router.push('/dashboard'), 1800)
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
          <p className="text-sm text-ink-50">Đang chuyển hướng đến trang học…</p>
        </div>
      </div>
    )
  }

  return (
    <AuthShell
      sectionNumber={2}
      sectionLabel="Đăng ký học sinh"
      title={<>Bắt đầu <em className="italic">hành trình</em>.</>}
      subtitle="Tạo tài khoản miễn phí — chỉ vài bước đơn giản."
      footer={
        <div className="flex flex-col gap-3 text-ink-50">
          <span>
            Đã có tài khoản?{' '}
            <Link href="/login" className="text-ink link-editorial">
              Đăng nhập
            </Link>
          </span>
          <Link href="/register/teacher" className="text-ink-50 hover:text-ink link-editorial">
            Bạn là giáo viên? Đăng ký giáo viên →
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
        <EditorialInput
          label="Họ và tên" required
          value={form.fullName}
          onChange={e => update('fullName', e.target.value)}
          placeholder="Nguyễn Văn A"
        />
        <div className="grid grid-cols-2 gap-6">
          <EditorialInput
            label="Lớp"
            value={form.className}
            onChange={e => update('className', e.target.value)}
            placeholder="12A1"
          />
          <EditorialInput
            label="Mã học sinh"
            value={form.studentCode}
            onChange={e => update('studentCode', e.target.value)}
            placeholder="HS001"
          />
        </div>
        <EditorialInput
          label="Email" type="email" required
          value={form.email}
          onChange={e => update('email', e.target.value)}
          placeholder="hocsinh@gmail.com"
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
          {loading ? 'Đang tạo tài khoản…' : 'Tạo tài khoản →'}
        </button>
      </form>
    </AuthShell>
  )
}
