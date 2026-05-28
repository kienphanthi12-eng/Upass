'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase'
import { AlertCircle } from 'lucide-react'
import AuthShell from '@/components/ui/AuthShell'
import EditorialInput from '@/components/ui/EditorialInput'

export default function LoginPage() {
  const router = useRouter()
  const supabase = createClient()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    const { data, error: err } = await supabase.auth.signInWithPassword({ email, password })
    setLoading(false)
    if (err) {
      setError('Email hoặc mật khẩu không đúng. Vui lòng thử lại.')
      return
    }
    if (data.user) {
      const { data: teacher } = await supabase
        .from('teachers')
        .select('id')
        .eq('id', data.user.id)
        .single()
      if (teacher) {
        router.push('/teacher/dashboard')
        router.refresh()
        return
      }
    }
    router.push('/dashboard')
    router.refresh()
  }

  return (
    <AuthShell
      sectionNumber={1}
      sectionLabel="Đăng nhập"
      title={<>Chào mừng <em className="italic">trở lại</em>.</>}
      subtitle="Tiếp tục hành trình chinh phục kỳ thi của bạn."
      footer={
        <div className="flex flex-col gap-3 text-ink-50">
          <span>
            Chưa có tài khoản?{' '}
            <Link href="/register" className="text-ink link-editorial">
              Đăng ký học sinh
            </Link>
          </span>
          <Link href="/teacher/login" className="text-ink-50 hover:text-ink link-editorial">
            Bạn là giáo viên? Đăng nhập tại đây →
          </Link>
        </div>
      }
    >
      <form onSubmit={handleLogin} className="flex flex-col gap-6">
        {error && (
          <div className="flex items-start gap-2 p-3 bg-ember-bg border-l-2 border-ember text-ember text-sm">
            <AlertCircle size={15} className="shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}
        <EditorialInput
          label="Email"
          type="email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          required
          placeholder="hocsinh@gmail.com"
        />
        <EditorialInput
          label="Mật khẩu"
          type="password"
          value={password}
          onChange={e => setPassword(e.target.value)}
          required
          placeholder="••••••••"
        />
        <button
          type="submit"
          disabled={loading}
          className="mt-4 w-full inline-flex items-center justify-center gap-2 py-4 bg-ink text-paper text-sm tracking-label hover:bg-moss transition-colors disabled:opacity-50"
        >
          {loading
            ? <span className="w-4 h-4 border border-paper/30 border-t-paper rounded-full animate-spin" />
            : null}
          {loading ? 'Đang đăng nhập…' : 'Đăng nhập →'}
        </button>
      </form>
    </AuthShell>
  )
}
