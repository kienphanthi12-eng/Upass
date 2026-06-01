'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useState, useEffect } from 'react'
import { createClient } from '@/lib/supabase'
import type { User } from '@supabase/supabase-js'
import { Menu, X } from 'lucide-react'
import Wordmark from './ui/Wordmark'
import CustomCursor from './ui/CustomCursor'

const navLinks = [
  { href: '/exams',       label: 'Đề thi' },
  { href: '/practice',    label: 'Luyện tập' },
  { href: '/leaderboard', label: 'Xếp hạng' },
  { href: '/pricing',     label: 'Bảng giá' },
  { href: '/blog',        label: 'Blog' },
]

export default function Header() {
  const pathname = usePathname()
  const router = useRouter()
  const [user, setUser] = useState<User | null>(null)
  const [studentName, setStudentName] = useState('')
  const [menuOpen, setMenuOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const supabase = createClient()

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      setUser(data.user)
      if (data.user) {
        supabase
          .from('students')
          .select('full_name')
          .eq('id', data.user.id)
          .single()
          .then(({ data: s }) => { if (s) setStudentName(s.full_name) })
      }
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_e, session) => {
      setUser(session?.user ?? null)
    })
    return () => subscription.unsubscribe()
  }, [supabase])

  const handleLogout = async () => {
    await supabase.auth.signOut()
    router.push('/')
    router.refresh()
  }

  return (
    <>
      <CustomCursor />
      <header className="sticky top-0 z-40 bg-paper/85 backdrop-blur-md border-b border-line">
        <div className="max-w-7xl mx-auto px-6 sm:px-10">
          <div className="flex items-center justify-between h-16 sm:h-20">

            {/* Wordmark */}
            <Wordmark size="md" />

            {/* Desktop nav */}
            <nav className="hidden md:flex items-center gap-10">
              {navLinks.map(({ href, label }) => {
                const active = pathname === href || pathname.startsWith(href + '/')
                return (
                  <Link
                    key={href}
                    href={href}
                    className={`text-sm tracking-label link-editorial transition-colors ${
                      active ? 'text-ink font-medium' : 'text-ink-50 hover:text-ink'
                    }`}
                  >
                    {label}
                  </Link>
                )
              })}
            </nav>

            {/* Right: auth */}
            <div className="flex items-center gap-6">
              {user ? (
                <div className="relative">
                  <button
                    onClick={() => setUserMenuOpen(v => !v)}
                    className="flex items-center gap-2.5 text-sm text-ink"
                  >
                    <div className="w-8 h-8 rounded-full bg-moss-bg flex items-center justify-center">
                      <span className="text-moss text-[11px] font-medium">
                        {studentName.trim().split(' ').pop()?.charAt(0)?.toUpperCase() ?? 'U'}
                      </span>
                    </div>
                    <span className="hidden sm:block max-w-32 truncate font-medium">
                      {studentName || 'Học sinh'}
                    </span>
                  </button>

                  {userMenuOpen && (
                    <div className="absolute right-0 mt-3 w-52 bg-snow border border-line py-2 z-50">
                      <Link
                        href="/dashboard"
                        onClick={() => setUserMenuOpen(false)}
                        className="block px-5 py-2.5 text-sm text-ink hover:bg-paper-soft"
                      >
                        Thống kê của tôi →
                      </Link>
                      <div className="border-t border-line my-1" />
                      <button
                        onClick={handleLogout}
                        className="block w-full text-left px-5 py-2.5 text-sm text-ember hover:bg-ember-bg"
                      >
                        Đăng xuất →
                      </button>
                    </div>
                  )}
                </div>
              ) : (
                <div className="hidden sm:flex items-center gap-8">
                  <Link
                    href="/login"
                    className="text-sm tracking-label text-ink-50 hover:text-ink link-editorial"
                  >
                    Đăng nhập
                  </Link>
                  <Link
                    href="/register"
                    className="inline-flex items-center gap-2 px-5 py-2.5 bg-ink text-paper text-sm tracking-label hover:bg-moss transition-colors"
                  >
                    Đăng ký <span aria-hidden>→</span>
                  </Link>
                </div>
              )}

              {/* Mobile menu */}
              <button
                className="md:hidden p-2 text-ink"
                onClick={() => setMenuOpen(v => !v)}
                aria-label="Menu"
              >
                {menuOpen ? <X size={20} /> : <Menu size={20} />}
              </button>
            </div>
          </div>

          {/* Mobile nav */}
          {menuOpen && (
            <div className="md:hidden py-4 border-t border-line space-y-1">
              {navLinks.map(({ href, label }) => {
                const active = pathname === href
                return (
                  <Link
                    key={href}
                    href={href}
                    onClick={() => setMenuOpen(false)}
                    className={`block px-2 py-3 text-sm tracking-label ${
                      active ? 'text-ink' : 'text-ink-50'
                    }`}
                  >
                    {label} →
                  </Link>
                )
              })}
              {!user && (
                <>
                  <div className="h-px bg-line my-2" />
                  <Link
                    href="/login"
                    onClick={() => setMenuOpen(false)}
                    className="block px-2 py-3 text-sm tracking-label text-ink-50"
                  >
                    Đăng nhập →
                  </Link>
                  <Link
                    href="/register"
                    onClick={() => setMenuOpen(false)}
                    className="block px-2 py-3 text-sm tracking-label text-ink"
                  >
                    Đăng ký →
                  </Link>
                </>
              )}
            </div>
          )}
        </div>
      </header>
    </>
  )
}
