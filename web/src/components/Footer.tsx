import Link from 'next/link'
import MarqueeStrip from './ui/MarqueeStrip'
import Logo from './ui/Logo'

const FOOTER_TICKER = [
  'Luyện thi THPT',
  '5.000+ đề thi',
  'OCR thế hệ mới',
  'AI Chatbot sắp ra mắt',
  'Có đếm giờ',
  'Phân tích kết quả',
]

export default function Footer() {
  return (
    <footer className="mt-auto bg-paper">
      {/* Display ticker — editorial signature */}
      <MarqueeStrip items={FOOTER_TICKER} size="lg" />

      <div className="max-w-7xl mx-auto px-6 sm:px-10 py-16 sm:py-20">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-10 md:gap-16">

          {/* Brand block */}
          <div className="md:col-span-5">
            <Logo variant="display" size="lg" />
            <p className="font-display text-2xl sm:text-3xl text-ink mt-8 leading-snug max-w-md">
              Nền tảng luyện thi <em className="font-display italic">trắc nghiệm</em> dành cho học sinh THPT.
            </p>
            <p className="text-sm text-ink-50 mt-4 max-w-md leading-relaxed">
              Ôn tập hiệu quả, theo dõi tiến bộ và tự tin bước vào kỳ thi tốt nghiệp.
            </p>
          </div>

          {/* Sitemap */}
          <div className="md:col-span-3">
            <p className="text-xs tracking-label text-ink-50 mb-5">(01) Khám phá</p>
            <ul className="space-y-3">
              {[
                { href: '/exams',       label: 'Đề thi' },
                { href: '/practice',    label: 'Luyện tập' },
                { href: '/leaderboard', label: 'Xếp hạng' },
                { href: '/dashboard',   label: 'Thống kê' },
                { href: '/pricing',     label: 'Bảng giá' },
              ].map(({ href, label }) => (
                <li key={href}>
                  <Link
                    href={href}
                    className="text-base text-ink hover:text-moss link-editorial"
                  >
                    {label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Contact */}
          <div className="md:col-span-4">
            <p className="text-xs tracking-label text-ink-50 mb-5">(02) Liên hệ</p>
            <ul className="space-y-3 text-base text-ink">
              <li>upass.io.vn</li>
              <li>
                <a href="mailto:kienphanthi12@gmail.com" className="link-editorial hover:text-moss">
                  kienphanthi12@gmail.com
                </a>
              </li>
              <li>
                <a href="tel:+84868508968" className="link-editorial hover:text-moss">
                  0868 508 968
                </a>
              </li>
            </ul>
            <div className="mt-8">
              <p className="text-xs tracking-label text-ink-50 mb-3">(03) Giáo viên</p>
              <Link
                href="/teacher/login"
                className="text-base text-ink hover:text-moss link-editorial"
              >
                Cổng giáo viên →
              </Link>
            </div>
          </div>
        </div>

        <div className="mt-16 pt-8 border-t border-line flex flex-col sm:flex-row items-start sm:items-end justify-between gap-4">
          <p className="text-xs tracking-label text-ink-50">© 2026 U-PASS — All rights reserved</p>
          <p className="text-xs tracking-label text-ink-50">
            Crafted in Hanoi · v1.0
          </p>
        </div>
      </div>
    </footer>
  )
}
