/**
 * Editorial section number — e.g. (01), (02) — tracking-widest
 * Use to label sections like a portfolio.
 */
export default function SectionNumber({
  n,
  label,
  className = '',
}: {
  n: number | string
  label?: string
  className?: string
}) {
  const num = typeof n === 'number' ? String(n).padStart(2, '0') : n
  return (
    <div className={`flex items-center gap-3 text-ink-50 text-xs tracking-label font-mono ${className}`}>
      <span>({num})</span>
      {label && <span>{label}</span>}
    </div>
  )
}
