'use client'

import { useRef, type ReactNode } from 'react'
import { motion, useInView } from 'motion/react'

/**
 * Editorial scroll reveal — fade + translate up when child enters viewport.
 * Use to wrap section headings, large blocks. Light & subtle.
 */
export default function ScrollReveal({
  children,
  delay = 0,
  duration = 0.7,
  y = 24,
  once = true,
  className = '',
  as: Tag = 'div',
}: {
  children: ReactNode
  delay?: number
  duration?: number
  y?: number
  once?: boolean
  className?: string
  as?: 'div' | 'section' | 'span' | 'h1' | 'h2' | 'h3' | 'p' | 'article'
}) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once, margin: '-10% 0px -10% 0px' })

  const MotionTag = motion[Tag] as typeof motion.div

  return (
    <MotionTag
      ref={ref}
      initial={{ opacity: 0, y }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration, delay, ease: [0.22, 1, 0.36, 1] }}
      className={className}
    >
      {children}
    </MotionTag>
  )
}
