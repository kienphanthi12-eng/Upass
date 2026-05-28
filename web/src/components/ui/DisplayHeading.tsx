import type { ReactNode } from 'react'

/**
 * Editorial display heading — Instrument Serif, big, tight tracking.
 * Use for hero/section H1 and H2.
 */
export default function DisplayHeading({
  children,
  as: Tag = 'h1',
  size = 'xl',
  className = '',
  italic = false,
}: {
  children: ReactNode
  as?: 'h1' | 'h2' | 'h3'
  size?: 'sm' | 'md' | 'lg' | 'xl' | '2xl'
  className?: string
  italic?: boolean
}) {
  const sizes = {
    sm:  'text-3xl sm:text-4xl',
    md:  'text-4xl sm:text-5xl',
    lg:  'text-5xl sm:text-6xl lg:text-7xl',
    xl:  'text-6xl sm:text-7xl lg:text-8xl',
    '2xl': 'text-7xl sm:text-8xl lg:text-9xl',
  }
  return (
    <Tag
      className={`font-display leading-[0.95] tracking-tight text-ink ${sizes[size]} ${italic ? 'italic' : ''} ${className}`}
    >
      {children}
    </Tag>
  )
}
