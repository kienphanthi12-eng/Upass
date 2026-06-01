import Link from 'next/link'

/**
 * U-PASS Logo system — editorial typographic mark.
 *
 * Variants:
 *  - mark:     Square SVG mark only (favicon/tiny size)
 *  - wordmark: Spaced "U · P · A · S · S" (compact horizontal)
 *  - display:  Italic serif "U·PASS" with moss caret accent (large hero use)
 *  - lockup:   Mark + spaced wordmark side by side (header standard)
 */

type Variant = 'mark' | 'wordmark' | 'display' | 'lockup'

interface LogoProps {
  variant?: Variant
  size?: 'sm' | 'md' | 'lg' | 'xl'
  href?: string | null
  className?: string
  /** Override mark color (default: currentColor for ink, moss for accent kept) */
  monochrome?: boolean
}

/* ─── The Mark: square with italic U + moss upward chevron ─── */
export function LogoMark({
  size = 36,
  monochrome = false,
  className = '',
}: { size?: number; monochrome?: boolean; className?: string }) {
  const accentColor = monochrome ? 'currentColor' : '#4a5d3a'
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 44 44"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`shrink-0 ${className}`}
      aria-label="U-PASS"
    >
      {/* Frame — thin ink border */}
      <rect
        x="0.75"
        y="0.75"
        width="42.5"
        height="42.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="0.75"
      />
      {/* Italic serif U */}
      <text
        x="22"
        y="32.5"
        fontFamily="var(--font-playfair), Georgia, serif"
        fontStyle="italic"
        fontSize="29"
        textAnchor="middle"
        fill="currentColor"
        style={{ letterSpacing: '0.5px' }}
      >
        U
      </text>
      {/* Moss upward chevron — top right corner */}
      <path
        d="M 31 9.5 L 34 6 L 37 9.5"
        fill="none"
        stroke={accentColor}
        strokeWidth="1.3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

/* ─── Display wordmark: italic serif U·PASS with moss caret ─── */
function DisplayWordmark({ className = '' }: { className?: string }) {
  return (
    <span className={`font-display italic leading-none ${className}`}>
      U
      <span className="inline-block mx-1 not-italic align-middle relative -top-1">
        <svg width="0.55em" height="0.55em" viewBox="0 0 12 12" className="text-moss inline-block">
          <path
            d="M 2 8 L 6 3 L 10 8"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </span>
      PASS
    </span>
  )
}

/* ─── Spaced wordmark — the everyday horizontal mark ─── */
function SpacedWordmark({ className = '' }: { className?: string }) {
  return (
    <span className={`tracking-wordmark font-medium whitespace-nowrap ${className}`}>
      U · P · A · S · S
    </span>
  )
}

const SPACED_SIZES = {
  sm: 'text-[10px]',
  md: 'text-xs',
  lg: 'text-sm',
  xl: 'text-base',
}
const DISPLAY_SIZES = {
  sm: 'text-2xl',
  md: 'text-4xl',
  lg: 'text-6xl',
  xl: 'text-7xl sm:text-8xl',
}
const MARK_PX = { sm: 22, md: 32, lg: 44, xl: 56 }

export default function Logo({
  variant = 'wordmark',
  size = 'md',
  href = '/',
  className = '',
  monochrome = false,
}: LogoProps) {
  let content: React.ReactNode

  if (variant === 'mark') {
    content = <LogoMark size={MARK_PX[size]} monochrome={monochrome} className={className} />
  } else if (variant === 'wordmark') {
    content = <SpacedWordmark className={`${SPACED_SIZES[size]} ${className}`} />
  } else if (variant === 'display') {
    content = <DisplayWordmark className={`${DISPLAY_SIZES[size]} ${className}`} />
  } else {
    // lockup: mark + spaced wordmark
    content = (
      <span className={`inline-flex items-center gap-3 whitespace-nowrap ${className}`}>
        <LogoMark size={MARK_PX[size]} monochrome={monochrome} />
        <SpacedWordmark className={SPACED_SIZES[size]} />
      </span>
    )
  }

  if (!href) return <span className="text-ink">{content}</span>
  return (
    <Link href={href} className="text-ink hover:text-moss transition-colors inline-block">
      {content}
    </Link>
  )
}
