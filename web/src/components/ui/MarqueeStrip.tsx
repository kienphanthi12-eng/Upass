/**
 * Continuous horizontal marquee — used as divider or footer strip.
 * Pass items[]. Repeated 2x for seamless loop via CSS.
 */
export default function MarqueeStrip({
  items,
  className = '',
  separator = '·',
  size = 'md',
}: {
  items: string[]
  className?: string
  separator?: string
  size?: 'sm' | 'md' | 'lg'
}) {
  const sizes = {
    sm: 'text-sm py-2',
    md: 'text-base py-3',
    lg: 'text-2xl sm:text-3xl py-5 font-display',
  }
  const content = [...items, ...items]
  return (
    <div className={`overflow-hidden border-y border-line ${sizes[size]} ${className}`}>
      <div className="flex animate-marquee whitespace-nowrap">
        {content.map((item, i) => (
          <span key={i} className="flex items-center px-4 sm:px-6 text-ink">
            <span>{item}</span>
            <span className="ml-4 sm:ml-6 text-ink-30">{separator}</span>
          </span>
        ))}
      </div>
    </div>
  )
}
