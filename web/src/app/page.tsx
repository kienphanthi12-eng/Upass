import Link from 'next/link'
import Header from '@/components/Header'
import Footer from '@/components/Footer'
import DisplayHeading from '@/components/ui/DisplayHeading'
import SectionNumber from '@/components/ui/SectionNumber'
import MarqueeStrip from '@/components/ui/MarqueeStrip'
import ScrollReveal from '@/components/ui/ScrollReveal'
import MagneticButton from '@/components/ui/MagneticButton'

const FEATURES = [
  {
    num: '01',
    title: 'Kho 5.000+ đề thi',
    body: 'Thư viện đề thi THPT lớn nhất Việt Nam — 5.000+ đề từ các trường, sở GD&ĐT và kỳ thi thử trên toàn quốc, cập nhật liên tục.',
  },
  {
    num: '02',
    title: 'OCR thế hệ mới cho giáo viên',
    body: 'Giáo viên tải PDF đề thi — hệ thống tự động trích xuất, nhận diện công thức toán học, bảng biểu, hình ảnh, rồi chuẩn hoá thành câu hỏi LaTeX trong vài phút. Không cần gõ tay.',
  },
  {
    num: '03',
    title: 'AI Chatbot — sắp ra mắt',
    body: 'Trợ lý AI riêng cho từng học sinh: giải thích từng bước, gợi ý cách tiếp cận, đề xuất câu hỏi luyện tập theo điểm yếu. Như có một gia sư 24/7.',
  },
  {
    num: '04',
    title: 'Thi có đếm giờ',
    body: 'Mô phỏng đúng điều kiện thi thật với đồng hồ đếm ngược — quen áp lực thời gian.',
  },
  {
    num: '05',
    title: 'Luyện theo chủ đề',
    body: 'Lọc câu hỏi theo chủ đề và mức độ Nhận biết / Thông hiểu / Vận dụng — ôn luyện có trọng tâm.',
  },
  {
    num: '06',
    title: 'Phân tích & xếp hạng',
    body: 'Xem chi tiết từng câu đúng/sai, thống kê điểm theo thời gian và so sánh thứ hạng với bạn cùng trường.',
  },
]

const HERO_TICKER = ['5.000+ đề thi', 'OCR tự động', 'AI Chatbot sắp ra mắt', '11 môn học', 'Có đếm giờ']

export default function LandingPage() {
  return (
    <>
      <Header />

      <main>
        {/* ─── (01) Hero ─────────────────────────────────────── */}
        <section className="relative">
          <div className="max-w-7xl mx-auto px-6 sm:px-10 pt-16 sm:pt-28 pb-16 sm:pb-24">
            <ScrollReveal>
              <SectionNumber n={1} label="Nền tảng" />
            </ScrollReveal>

            <ScrollReveal delay={0.1}>
              <DisplayHeading size="2xl" className="mt-8 max-w-5xl">
                Chinh phục kỳ thi <em className="font-display italic text-moss">THPT</em>
                <br />
                bằng cách khác biệt.
              </DisplayHeading>
            </ScrollReveal>

            <ScrollReveal delay={0.2}>
              <div className="mt-12 max-w-2xl">
                <p className="text-lg sm:text-xl text-ink-70 leading-relaxed">
                  Luyện tập với hàng nghìn câu hỏi trắc nghiệm được phân loại theo chuẩn,
                  thi thử có đếm giờ và theo dõi tiến bộ của bạn mỗi ngày.
                </p>
              </div>
            </ScrollReveal>

            <ScrollReveal delay={0.35}>
              <div className="mt-12 flex flex-wrap items-center gap-6">
                <MagneticButton href="/register" variant="primary">
                  Bắt đầu luyện thi <span aria-hidden>→</span>
                </MagneticButton>
                <Link
                  href="/exams"
                  className="text-base tracking-label text-ink link-editorial"
                >
                  Xem đề thi
                </Link>
              </div>
            </ScrollReveal>
          </div>

          {/* Ticker below hero */}
          <MarqueeStrip items={HERO_TICKER} size="md" />
        </section>

        {/* ─── (02) Why U-PASS ───────────────────────────────── */}
        <section className="bg-paper-soft">
          <div className="max-w-7xl mx-auto px-6 sm:px-10 py-20 sm:py-28">
            <div className="grid grid-cols-12 gap-8">
              <div className="col-span-12 md:col-span-4">
                <ScrollReveal>
                  <SectionNumber n={2} label="Tại sao U-PASS" />
                  <DisplayHeading size="lg" as="h2" className="mt-6 max-w-md">
                    Sáu lý do để chọn <em className="italic">chúng tôi</em>.
                  </DisplayHeading>
                </ScrollReveal>
              </div>

              <div className="col-span-12 md:col-span-8 md:col-start-5">
                <ul>
                  {FEATURES.map((f, i) => (
                    <ScrollReveal key={f.num} delay={i * 0.07} as="div">
                      <li className="group grid grid-cols-12 gap-6 items-baseline border-t border-line py-7 cursor-default">
                        <span className="col-span-2 sm:col-span-1 text-xs tracking-label text-ink-50 font-mono">
                          ({f.num})
                        </span>
                        <div className="col-span-10 sm:col-span-11 grid sm:grid-cols-12 gap-3 sm:gap-8">
                          <h3 className="sm:col-span-4 font-display text-2xl sm:text-3xl text-ink group-hover:italic transition-all">
                            {f.title}
                          </h3>
                          <p className="sm:col-span-8 text-base text-ink-70 leading-relaxed">
                            {f.body}
                          </p>
                        </div>
                      </li>
                    </ScrollReveal>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </section>

        {/* ─── (03) Numbers ──────────────────────────────────── */}
        <section>
          <div className="max-w-7xl mx-auto px-6 sm:px-10 py-20 sm:py-28">
            <ScrollReveal>
              <SectionNumber n={3} label="Con số" />
            </ScrollReveal>

            <div className="mt-12 grid grid-cols-2 md:grid-cols-4 gap-y-12 gap-x-8">
              {[
                { v: '5.000+', l: 'đề thi' },
                { v: 'OCR',    l: 'thế hệ mới' },
                { v: 'AI',     l: 'chatbot' },
                { v: '11',     l: 'môn học' },
              ].map((stat, i) => (
                <ScrollReveal key={stat.l} delay={i * 0.08}>
                  <div>
                    <p className="font-display text-6xl sm:text-7xl lg:text-8xl text-ink leading-none">
                      {stat.v}
                    </p>
                    <p className="mt-3 text-xs tracking-label text-ink-50">{stat.l}</p>
                  </div>
                </ScrollReveal>
              ))}
            </div>
          </div>
        </section>

        {/* ─── (04) CTA ──────────────────────────────────────── */}
        <section className="bg-ink text-paper">
          <div className="max-w-7xl mx-auto px-6 sm:px-10 py-24 sm:py-32 text-center">
            <ScrollReveal>
              <p className="text-xs tracking-label text-paper/50">(04) Bắt đầu</p>
            </ScrollReveal>
            <ScrollReveal delay={0.1}>
              <h2 className="font-display text-5xl sm:text-7xl lg:text-8xl mt-8 leading-[0.95] max-w-4xl mx-auto">
                Sẵn sàng <em className="italic">chinh phục</em>?
              </h2>
            </ScrollReveal>
            <ScrollReveal delay={0.25}>
              <div className="mt-14 inline-flex flex-wrap items-center justify-center gap-6">
                <Link
                  href="/register"
                  className="inline-flex items-center gap-3 px-8 py-4 bg-paper text-ink text-sm tracking-label hover:bg-moss hover:text-paper transition-colors"
                >
                  Tạo tài khoản miễn phí <span aria-hidden>→</span>
                </Link>
                <Link
                  href="/login"
                  className="text-sm tracking-label text-paper/70 link-editorial"
                >
                  Đã có tài khoản?
                </Link>
              </div>
            </ScrollReveal>
          </div>
        </section>
      </main>

      <Footer />
    </>
  )
}
