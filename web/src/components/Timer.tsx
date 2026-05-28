'use client'

import { useEffect, useState } from 'react'
import { Clock } from 'lucide-react'

interface TimerProps {
  initialSeconds: number
  onTimeUp: () => void
  paused?: boolean
}

export default function Timer({ initialSeconds, onTimeUp, paused = false }: TimerProps) {
  const [seconds, setSeconds] = useState(initialSeconds)

  useEffect(() => {
    if (paused || seconds <= 0) return
    const id = setInterval(() => {
      setSeconds(s => {
        if (s <= 1) {
          clearInterval(id)
          onTimeUp()
          return 0
        }
        return s - 1
      })
    }, 1000)
    return () => clearInterval(id)
  }, [paused, onTimeUp])

  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  const pct = seconds / initialSeconds
  const urgent = seconds < 300

  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-mono font-semibold transition-colors ${
      urgent ? 'bg-red-50 text-red-600 border border-red-200' : 'bg-navy-50 text-navy border border-navy-100'
    }`}>
      <Clock size={15} className={urgent ? 'text-red-500 animate-pulse' : 'text-gold'} />
      <span>
        {String(mins).padStart(2, '0')}:{String(secs).padStart(2, '0')}
      </span>
    </div>
  )
}
