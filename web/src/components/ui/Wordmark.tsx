import Logo from './Logo'

/**
 * @deprecated Use <Logo variant="lockup"> instead.
 * Kept for backwards compatibility — now renders the lockup (mark + spaced wordmark).
 */
export default function Wordmark({
  size = 'md',
  href = '/',
  className = '',
}: {
  size?: 'sm' | 'md' | 'lg' | 'xl'
  href?: string | null
  className?: string
}) {
  return <Logo variant="lockup" size={size} href={href} className={className} />
}
