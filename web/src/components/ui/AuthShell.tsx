import Link from 'next/link'
import type { ReactNode } from 'react'
import Wordmark from './Wordmark'
import SectionNumber from './SectionNumber'
import DisplayHeading from './DisplayHeading'

/**
 * Shared editorial layout for login + register pages.
 * Single column, centered, no navy side panel.
 */
export default function AuthShell({
  sectionNumber,
  sectionLabel,
  title,
  subtitle,
  children,
  footer,
}: {
  sectionNumber: number
  sectionLabel: string
  title: ReactNode
  subtitle?: string
  children: ReactNode
  footer?: ReactNode
}) {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Slim header */}
      <header className="px-6 sm:px-10 py-6 flex items-center justify-between border-b border-line">
        <Wordmark size="md" />
        <Link
          href="/"
          className="text-xs tracking-label text-ink-50 hover:text-ink link-editorial"
        >
          ← Trang chủ
        </Link>
      </header>

      <main className="flex-1 flex items-center justify-center px-6 sm:px-10 py-12 sm:py-20">
        <div className="w-full max-w-md">
          <SectionNumber n={sectionNumber} label={sectionLabel} />
          <DisplayHeading size="md" className="mt-6 mb-4 leading-tight">
            {title}
          </DisplayHeading>
          {subtitle && <p className="text-base text-ink-70 mb-10">{subtitle}</p>}
          {children}
          {footer && (
            <div className="mt-10 pt-8 border-t border-line text-sm">{footer}</div>
          )}
        </div>
      </main>
    </div>
  )
}
