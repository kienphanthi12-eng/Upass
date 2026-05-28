'use client'

import { useState, type InputHTMLAttributes, type ReactNode } from 'react'
import { Eye, EyeOff } from 'lucide-react'

/**
 * Editorial input — no border box, underline only, animates on focus.
 * Used across all auth + form pages.
 */
type Props = Omit<InputHTMLAttributes<HTMLInputElement>, 'type' | 'placeholder'> & {
  label: ReactNode
  type?: string
  required?: boolean
  hint?: string
  placeholder?: string
}

export default function EditorialInput({
  label,
  type = 'text',
  required,
  hint,
  className = '',
  id,
  ...rest
}: Props) {
  const [show, setShow] = useState(false)
  const isPassword = type === 'password'
  const actualType = isPassword && show ? 'text' : type
  const labelKey = typeof label === 'string' ? label : 'field'
  const inputId = id || `input-${labelKey.replace(/\s+/g, '-').toLowerCase()}`

  return (
    <div className={className}>
      <label
        htmlFor={inputId}
        className="block text-xs tracking-label text-ink-50 mb-2"
      >
        {label}{required && <span className="text-moss ml-1">*</span>}
      </label>
      <div className="relative">
        <input
          {...rest}
          id={inputId}
          type={actualType}
          required={required}
          className="w-full bg-transparent border-0 border-b border-line py-3 pr-10 text-base text-ink placeholder:text-ink-30 focus:outline-none focus:border-ink transition-colors"
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setShow(s => !s)}
            tabIndex={-1}
            className="absolute right-0 top-1/2 -translate-y-1/2 p-2 text-ink-30 hover:text-ink"
          >
            {show ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        )}
      </div>
      {hint && <p className="mt-1.5 text-xs text-ink-30">{hint}</p>}
    </div>
  )
}
