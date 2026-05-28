'use client'

import { useRef, type ReactNode, type MouseEvent } from 'react'
import { motion, useMotionValue, useSpring } from 'motion/react'

/**
 * Editorial magnetic button — pulls toward cursor with spring physics.
 * Use for primary CTAs on the landing + auth pages.
 */
export default function MagneticButton({
  children,
  onClick,
  type = 'button',
  className = '',
  variant = 'primary',
  href,
  disabled = false,
}: {
  children: ReactNode
  onClick?: () => void
  type?: 'button' | 'submit'
  className?: string
  variant?: 'primary' | 'outline' | 'ghost'
  href?: string
  disabled?: boolean
}) {
  const ref = useRef<HTMLElement>(null)
  const x = useMotionValue(0)
  const y = useMotionValue(0)
  const xs = useSpring(x, { stiffness: 200, damping: 18, mass: 0.4 })
  const ys = useSpring(y, { stiffness: 200, damping: 18, mass: 0.4 })

  const handleMove = (e: MouseEvent<HTMLElement>) => {
    if (!ref.current) return
    const rect = ref.current.getBoundingClientRect()
    const cx = rect.left + rect.width / 2
    const cy = rect.top + rect.height / 2
    x.set((e.clientX - cx) * 0.25)
    y.set((e.clientY - cy) * 0.25)
  }
  const handleLeave = () => { x.set(0); y.set(0) }

  const variants = {
    primary: 'bg-ink text-paper hover:bg-moss',
    outline: 'border border-ink text-ink hover:bg-ink hover:text-paper',
    ghost:   'text-ink hover:text-moss',
  }

  const base = `inline-flex items-center gap-2 px-7 py-3.5 text-sm tracking-label transition-colors duration-300 disabled:opacity-40 ${variants[variant]} ${className}`

  if (href) {
    return (
      <motion.a
        ref={ref as React.RefObject<HTMLAnchorElement>}
        href={href}
        onMouseMove={handleMove}
        onMouseLeave={handleLeave}
        style={{ x: xs, y: ys }}
        className={base}
      >
        {children}
      </motion.a>
    )
  }

  return (
    <motion.button
      ref={ref as React.RefObject<HTMLButtonElement>}
      type={type}
      onClick={onClick}
      onMouseMove={handleMove}
      onMouseLeave={handleLeave}
      disabled={disabled}
      style={{ x: xs, y: ys }}
      className={base}
    >
      {children}
    </motion.button>
  )
}
