'use client'

export default function CustomOwlSVG({ size = 120, className = '' }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`text-ink ${className}`}
    >
      {/* Ear tufts */}
      <path
        d="M 28 22 L 17 11 L 32 19"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M 72 22 L 83 11 L 68 19"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* Body */}
      <path
        d="M 50 15 C 31 15 24 28 24 50 C 24 72 31 84 50 84 C 69 84 76 72 76 50 C 76 28 69 15 50 15 Z"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
      {/* Big Glasses circles */}
      <circle cx="38" cy="40" r="10.5" stroke="currentColor" strokeWidth="1.75" />
      <circle cx="62" cy="40" r="10.5" stroke="currentColor" strokeWidth="1.75" />
      {/* Glasses bridge */}
      <path d="M 48.5 40 L 51.5 40" stroke="currentColor" strokeWidth="1.75" />
      {/* Eyes Pupils */}
      <circle cx="38" cy="40" r="2.5" fill="currentColor" />
      <circle cx="62" cy="40" r="2.5" fill="currentColor" />
      {/* Beak */}
      <path d="M 50 48 L 47.5 53 L 52.5 53 Z" fill="currentColor" />
      {/* Cheeks lines */}
      <path d="M 28 50 C 31 52 33 52 36 50" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" />
      <path d="M 72 50 C 69 52 67 52 64 50" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" />
      {/* Feather chest details */}
      <path d="M 46 59 Q 50 62 54 59" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M 42 66 Q 50 70 58 66" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      {/* Feet / Claws */}
      <path d="M 40 84 L 38 89" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
      <path d="M 43 84 L 43 89" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
      <path d="M 46 84 L 48 89" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
      <path d="M 54 84 L 52 89" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
      <path d="M 57 84 L 57 89" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
      <path d="M 60 84 L 62 89" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
      {/* Graduation mortarboard - offset slightly */}
      <path d="M 33 16 L 50 11 L 67 16 L 50 21 Z" fill="var(--color-moss-bg)" stroke="var(--color-moss)" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M 50 21 L 50 25" stroke="var(--color-moss)" strokeWidth="1.5" />
      <path d="M 60 17.5 L 63 23 L 61 24" fill="none" stroke="var(--color-moss)" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
