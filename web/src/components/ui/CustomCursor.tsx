'use client'

import { useEffect, useState } from 'react'
import { motion, useMotionValue, useSpring } from 'motion/react'
import { Pencil } from 'lucide-react'

/**
 * Editorial custom cursor — renders a pencil icon that follows the pointer instantly,
 * with a lagging ink dot that follows with spring physics.
 * Mounts globally via the Header / providers. Auto-disables on touch.
 */
export default function CustomCursor() {
  const x = useMotionValue(-100)
  const y = useMotionValue(-100)
  const sx = useSpring(x, { stiffness: 400, damping: 30, mass: 0.2 })
  const sy = useSpring(y, { stiffness: 400, damping: 30, mass: 0.2 })

  const [hover, setHover] = useState(false)
  const [touch, setTouch] = useState(false)

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const isTouch = window.matchMedia('(hover: none)').matches
      if (isTouch) {
        setTimeout(() => setTouch(true), 0)
      }
    }
  }, [])

  useEffect(() => {
    if (touch) return

    const move = (e: MouseEvent) => {
      x.set(e.clientX)
      y.set(e.clientY)
    }
    const over = (e: MouseEvent) => {
      const t = e.target as HTMLElement
      if (t.closest('a, button, [role="button"], input, textarea, select, [data-cursor-hover]')) {
        setHover(true)
      } else {
        setHover(false)
      }
    }

    window.addEventListener('mousemove', move)
    window.addEventListener('mouseover', over)
    document.body.classList.add('cursor-hidden')
    return () => {
      window.removeEventListener('mousemove', move)
      window.removeEventListener('mouseover', over)
      document.body.classList.remove('cursor-hidden')
    }
  }, [x, y, touch])

  if (touch) return null

  return (
    <>
      {/* Lagging ink/pencil trace dot */}
      <motion.div
        className="fixed top-0 left-0 pointer-events-none z-[9999] rounded-full"
        style={{
          x: sx, y: sy,
          translateX: '-50%', translateY: '-50%',
          width: hover ? 8 : 4,
          height: hover ? 8 : 4,
          backgroundColor: hover ? 'var(--color-moss)' : 'var(--color-ink-30)',
          opacity: 0.6,
          transition: 'width 0.2s ease, height 0.2s ease, background-color 0.2s ease',
        }}
      />

      {/* Primary Pencil Cursor */}
      <motion.div
        className="fixed top-0 left-0 pointer-events-none z-[9999]"
        style={{
          x, y,
          translateX: '-3px',
          translateY: '-20px',
        }}
      >
        <motion.div
          animate={{
            rotate: hover ? -15 : 0,
            scale: hover ? 1.15 : 1,
            color: hover ? 'var(--color-moss)' : 'var(--color-ink)',
          }}
          transition={{ type: 'spring', stiffness: 300, damping: 18 }}
        >
          <Pencil
            size={20}
            className="fill-paper stroke-[1.8px]"
          />
        </motion.div>
      </motion.div>
    </>
  )
}
