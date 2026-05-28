'use client'

import { useEffect, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import { createClient } from '@/lib/supabase'
import Wordmark from '@/components/ui/Wordmark'
import { Menu, X } from 'lucide-react'

const NAV = [
  { href: '/teacher/dashboard', label: 'Tổng quan' },
  { href: '/teacher/upload',    label: 'Tải đề PDF' },
  { href: '/teacher/matrix',    label: 'Ma trận đề' },
  { href: '/teacher/exams',     label: 'Đề đã đăng' },
  { href: '/teacher/students',  label: 'Học sinh' },
  { href: '/teacher/classes',   label: 'Lớp học' },
  { href: '/teacher/issues',    label: 'Báo lỗi' },
]

export default function TeacherLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const supabase = createClient()
  const [teacherName, setTeacherName] = useState('')
  const [checking, setChecking] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  useEffect(() => {
    async function check() {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) { router.push('/teacher/login'); return }

      const { data: teacher } = await supabase
        .from('teachers')
        .select('full_name')
        .eq('id', user.id)
        .single()

      if (!teacher) {
        setForbidden(true)
        setChecking(false)
        return
      }
      setTeacherName(teacher.full_name)
      setChecking(false)
    }
    check()
  }, [])

  const handleLogout = async () => {
    await supabase.auth.signOut()
    router.push('/teacher/login')
  }

  if (checking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-paper">
        <p className="font-display text-3xl text-ink-50 italic">Đang xác thực…</p>
      </div>
    )
  }

  if (forbidden) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-paper p-6">
        <div className="text-center max-w-md">
          <p className="text-xs tracking-label text-ember">Truy cập bị từ chối</p>
          <p className="font-display text-4xl text-ink mt-4 mb-3">
            Không có <em className="italic">quyền truy cập</em>.
          </p>
          <p className="text-base text-ink-50 mb-8">
            Tài khoản này không phải giáo viên. Vui lòng đăng nhập bằng tài khoản giáo viên.
          </p>
          <button
            onClick={handleLogout}
            className="inline-flex items-center gap-2 px-6 py-3 bg-ink text-paper text-sm tracking-label hover:bg-moss transition-colors"
          >
            Đăng xuất & quay lại →
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col lg:flex-row bg-paper">
      {/* Mobile top bar */}
      <div className="lg:hidden sticky top-0 z-30 bg-paper/95 backdrop-blur-md border-b border-line px-6 py-4 flex items-center justify-between">
        <button
          onClick={() => setMobileMenuOpen(true)}
          className="p-1 -ml-1 text-ink hover:text-moss"
          aria-label="Open menu"
        >
          <Menu size={24} />
        </button>
        <Wordmark size="sm" />
        <div className="w-6 h-6" /> {/* Spacer to center */}
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div 
          className="fixed inset-0 z-50 lg:hidden flex"
          onClick={() => setMobileMenuOpen(false)}
        >
          {/* Backdrop */}
          <div className="fixed inset-0 bg-ink/40 backdrop-blur-sm" />
          
          {/* Drawer Content */}
          <aside 
            className="relative w-64 bg-paper-soft border-r border-line h-full flex flex-col z-10 animate-in slide-in-from-left duration-200"
            onClick={e => e.stopPropagation()}
          >
            <div className="px-6 py-7 border-b border-line flex items-center justify-between">
              <div>
                <Wordmark size="md" />
                <p className="text-xs tracking-label text-ink-50 mt-3">Cổng giáo viên</p>
              </div>
              <button 
                onClick={() => setMobileMenuOpen(false)}
                className="p-1 text-ink-50 hover:text-ink"
                aria-label="Close menu"
              >
                <X size={20} />
              </button>
            </div>

            <nav className="flex-1 px-3 py-6 overflow-y-auto">
              {NAV.map(({ href, label }) => {
                const active = pathname === href || pathname.startsWith(href + '/')
                return (
                  <Link
                    key={href}
                    href={href}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`relative block px-4 py-3 text-sm tracking-label transition-colors ${
                      active
                        ? 'text-ink'
                        : 'text-ink-50 hover:text-ink'
                    }`}
                  >
                    {active && (
                      <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-ink" />
                    )}
                    {label}
                    {active && <span className="ml-2 text-ink-30">→</span>}
                  </Link>
                )
              })}
            </nav>

            <div className="px-6 py-6 border-t border-line">
              <p className="text-xs tracking-label text-ink-50 mb-1">Đăng nhập với</p>
              <p className="text-sm text-ink truncate mb-4">{teacherName}</p>
              <button
                onClick={handleLogout}
                className="text-xs tracking-label text-ink-50 hover:text-ink link-editorial"
              >
                Đăng xuất →
              </button>
            </div>
          </aside>
        </div>
      )}

      {/* Desktop Sidebar — editorial cream */}
      <aside className="hidden lg:flex w-64 bg-paper-soft border-r border-line flex-col shrink-0">
        <div className="px-6 py-7 border-b border-line">
          <Wordmark size="md" />
          <p className="text-xs tracking-label text-ink-50 mt-3">Cổng giáo viên</p>
        </div>

        <nav className="flex-1 px-3 py-6">
          {NAV.map(({ href, label }) => {
            const active = pathname === href || pathname.startsWith(href + '/')
            return (
              <Link
                key={href}
                href={href}
                className={`relative block px-4 py-3 text-sm tracking-label transition-colors ${
                  active
                    ? 'text-ink'
                    : 'text-ink-50 hover:text-ink'
                }`}
              >
                {active && (
                  <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-ink" />
                )}
                {label}
                {active && <span className="ml-2 text-ink-30">→</span>}
              </Link>
            )
          })}
        </nav>

        <div className="px-6 py-6 border-t border-line">
          <p className="text-xs tracking-label text-ink-50 mb-1">Đăng nhập với</p>
          <p className="text-sm text-ink truncate mb-4">{teacherName}</p>
          <button
            onClick={handleLogout}
            className="text-xs tracking-label text-ink-50 hover:text-ink link-editorial"
          >
            Đăng xuất →
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  )
}
