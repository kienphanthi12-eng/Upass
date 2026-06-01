'use client'

import { useState } from 'react'
import Header from '@/components/Header'
import Footer from '@/components/Footer'
import DisplayHeading from '@/components/ui/DisplayHeading'
import ScrollReveal from '@/components/ui/ScrollReveal'
import SectionNumber from '@/components/ui/SectionNumber'
import Logo, { LogoMark } from '@/components/ui/Logo'
import CustomOwlSVG from '@/components/ui/CustomOwlSVG'

// Define color palette data
const COLORS = [
  {
    name: 'Paper (Kem giấy)',
    variable: '--color-paper',
    hex: '#f5f1ea',
    text: 'text-ink',
    bg: 'bg-paper',
    border: 'border-line',
    desc: 'Màu nền giấy kem ấm áp cổ điển. Giúp mắt thư giãn khi đọc tài liệu và thi cử trong thời gian dài.'
  },
  {
    name: 'Paper Soft (Kem phân vùng)',
    variable: '--color-paper-soft',
    hex: '#ebe6dc',
    text: 'text-ink',
    bg: 'bg-paper-soft',
    border: 'border-line',
    desc: 'Màu nền phụ cho các khối thẻ, thanh bên, hoặc phân tách các phần trong tài liệu.'
  },
  {
    name: 'Ink (Mực tối)',
    variable: '--color-ink',
    hex: '#1a1814',
    text: 'text-paper',
    bg: 'bg-ink',
    border: 'border-ink',
    desc: 'Màu chữ chính và màu đen mực đặc trưng. Tránh dùng màu đen gắt (#000) để đem lại cảm giác tự nhiên.'
  },
  {
    name: 'Moss (Rêu học thuật)',
    variable: '--color-moss',
    hex: '#4a5d3a',
    text: 'text-paper',
    bg: 'bg-moss',
    border: 'border-moss',
    desc: 'Màu nhấn chính thương hiệu. Biểu trưng cho sự kiên trì, tập trung trí tuệ và sự trưởng thành học thuật.'
  },
  {
    name: 'Ember (Rust Orange)',
    variable: '--color-ember',
    hex: '#b54a2b',
    text: 'text-paper',
    bg: 'bg-ember',
    border: 'border-ember',
    desc: 'Màu trạng thái lỗi hoặc câu trả lời sai. Được làm dịu và đằm màu theo phong cách báo chí truyền thống.'
  },
  {
    name: 'Sun (Mustard Yellow)',
    variable: '--color-sun',
    hex: '#a8851f',
    text: 'text-paper',
    bg: 'bg-sun',
    border: 'border-sun',
    desc: 'Màu trạng thái cảnh báo hoặc nhắc nhở. Tông mù tạt nhã nhặn đồng bộ với màu giấy.'
  }
]

// SVG Logos for copy-paste action
const LOGO_SVGS = {
  mark: `<svg width="44" height="44" viewBox="0 0 44 44" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="0.75" y="0.75" width="42.5" height="42.5" fill="none" stroke="#1a1814" stroke-width="0.75"/>
  <text x="22" y="32.5" font-family="Georgia, serif" font-style="italic" font-size="29" text-anchor="middle" fill="#1a1814">U</text>
  <path d="M 31 9.5 L 34 6 L 37 9.5" fill="none" stroke="#4a5d3a" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>
</svg>`,
  wordmark: `<span class="tracking-wordmark font-medium text-xs">U · P · A · S · S</span>`,
  display: `<span class="font-display italic text-4xl">U <span class="inline-block mx-1 not-italic"><svg width="0.55em" height="0.55em" viewBox="0 0 12 12" class="text-moss inline-block"><path d="M 2 8 L 6 3 L 10 8" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg></span> PASS</span>`
}

export default function BrandHubPage() {
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [fontSizeBase, setFontSizeBase] = useState(16)

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  return (
    <>
      <Header />

      <main className="min-h-screen bg-paper pb-24">
        {/* ─── (01) Hero Section ────────────────────────────── */}
        <section className="border-b border-line">
          <div className="max-w-7xl mx-auto px-6 sm:px-10 py-16 sm:py-24">
            <ScrollReveal>
              <SectionNumber n={1} label="Identity Hub" />
            </ScrollReveal>

            <ScrollReveal delay={0.1}>
              <DisplayHeading size="xl" className="mt-6 max-w-4xl">
                Cẩm nang <em className="italic font-display text-moss">Thương Hiệu</em> U-PASS
              </DisplayHeading>
            </ScrollReveal>

            <ScrollReveal delay={0.2}>
              <div className="mt-8 max-w-2xl">
                <p className="text-lg text-ink-70 leading-relaxed font-sans">
                  Quy chuẩn thiết kế, hệ thống logo, bảng màu và linh vật học thuật chính thức của U-PASS. 
                  Thiết kế được định hình theo phong cách **Editorial (Ấn phẩm báo chí học thuật)** mang tính tối giản, 
                  tập trung cao độ và đậm chất tri thức.
                </p>
              </div>
            </ScrollReveal>
          </div>
        </section>

        {/* ─── (02) Core Philosophy ─────────────────────────── */}
        <section className="border-b border-line bg-paper-soft/30">
          <div className="max-w-7xl mx-auto px-6 sm:px-10 py-16 sm:py-24">
            <div className="grid grid-cols-12 gap-8">
              <div className="col-span-12 md:col-span-4">
                <ScrollReveal>
                  <SectionNumber n={2} label="Triết lý cốt lõi" />
                  <h2 className="font-display text-3xl sm:text-4xl text-ink mt-4">
                    Bản sắc của <em className="italic">chúng tôi</em>.
                  </h2>
                </ScrollReveal>
              </div>

              <div className="col-span-12 md:col-span-8 grid sm:grid-cols-2 gap-8">
                <ScrollReveal delay={0.1}>
                  <div className="border-t border-line pt-6">
                    <span className="text-xs font-mono text-ink-50 font-semibold uppercase tracking-wider">(01) Không gian tĩnh lặng</span>
                    <h3 className="font-display text-xl text-ink mt-3 font-semibold">Distraction-Free Sanctuary</h3>
                    <p className="mt-2 text-sm text-ink-70 leading-relaxed">
                      Loại bỏ hoàn toàn các yếu tố gây mất tập trung như quảng cáo nhấp nháy, các hiệu ứng game hóa màu mè. 
                      U-PASS mang lại cảm giác học trên giấy in thực thụ.
                    </p>
                  </div>
                </ScrollReveal>

                <ScrollReveal delay={0.2}>
                  <div className="border-t border-line pt-6">
                    <span className="text-xs font-mono text-ink-50 font-semibold uppercase tracking-wider">(02) Tính chuẩn xác học thuật</span>
                    <h3 className="font-display text-xl text-ink mt-3 font-semibold">Academic Integrity</h3>
                    <p className="mt-2 text-sm text-ink-70 leading-relaxed">
                      Sử dụng hệ thống chữ LaTeX sắc nét, OCR trích xuất công thức toán lý hóa hoàn hảo. 
                      Mỗi dòng chữ đều thể hiện tính học thuật nghiêm túc, tôn trọng khoa học.
                    </p>
                  </div>
                </ScrollReveal>

                <ScrollReveal delay={0.3}>
                  <div className="border-t border-line pt-6">
                    <span className="text-xs font-mono text-ink-50 font-semibold uppercase tracking-wider">(03) AI Trợ lý Cú Mèo</span>
                    <h3 className="font-display text-xl text-ink mt-3 font-semibold">Empathetic AI Companion</h3>
                    <p className="mt-2 text-sm text-ink-70 leading-relaxed">
                      Mascot Cú Mèo U-PASS không giải hộ mà dẫn dắt học sinh suy luận. 
                      Xưng hô "Cú Mèo" - "sĩ tử" tạo không gian đối thoại gần gũi, khích lệ và đồng hành.
                    </p>
                  </div>
                </ScrollReveal>

                <ScrollReveal delay={0.4}>
                  <div className="border-t border-line pt-6">
                    <span className="text-xs font-mono text-ink-50 font-semibold uppercase tracking-wider">(04) Vẻ đẹp báo chí in ấn</span>
                    <h3 className="font-display text-xl text-ink mt-3 font-semibold">Editorial Aesthetics</h3>
                    <p className="mt-2 text-sm text-ink-70 leading-relaxed">
                      Tận dụng lưới bố cục tạp chí, font chữ Serif thanh mảnh đi kèm Sans tối giản, 
                      kết hợp kỹ thuật in mực đen (Ink) trên nền giấy kem ấm (Paper).
                    </p>
                  </div>
                </ScrollReveal>
              </div>
            </div>
          </div>
        </section>

        {/* ─── (03) Logo System ─────────────────────────────── */}
        <section className="border-b border-line">
          <div className="max-w-7xl mx-auto px-6 sm:px-10 py-16 sm:py-24">
            <ScrollReveal>
              <SectionNumber n={3} label="Hệ thống Logo" />
              <h2 className="font-display text-3xl sm:text-4xl text-ink mt-4 mb-12">
                Các biến thể <em className="italic">Logo chính thức</em>
              </h2>
            </ScrollReveal>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {/* LogoMark */}
              <ScrollReveal delay={0.1}>
                <div className="border border-line bg-snow p-8 flex flex-col h-full justify-between card-shadow">
                  <div>
                    <span className="text-xs font-mono text-ink-50 font-semibold uppercase tracking-wider">01. LogoMark (Biểu trưng)</span>
                    <div className="my-8 flex justify-center items-center h-28">
                      <LogoMark size={56} />
                    </div>
                  </div>
                  <div>
                    <p className="text-xs text-ink-70 mb-4 leading-relaxed">
                      Biểu tượng đại diện thu nhỏ gồm khung chữ nhật mảnh, ký tự U in nghiêng và dấu mũ hướng lên màu Moss biểu trưng cho sự tiến bước.
                    </p>
                    <button
                      onClick={() => handleCopy('logomark', LOGO_SVGS.mark)}
                      className="w-full text-center py-2.5 bg-paper hover:bg-moss hover:text-paper border border-line text-xs font-semibold tracking-label transition-colors"
                    >
                      {copiedId === 'logomark' ? 'ĐÃ SAO CHÉP SVG! ✓' : 'SAO CHÉP MÃ SVG'}
                    </button>
                  </div>
                </div>
              </ScrollReveal>

              {/* Spaced Wordmark */}
              <ScrollReveal delay={0.2}>
                <div className="border border-line bg-snow p-8 flex flex-col h-full justify-between card-shadow">
                  <div>
                    <span className="text-xs font-mono text-ink-50 font-semibold uppercase tracking-wider">02. Spaced Wordmark</span>
                    <div className="my-8 flex justify-center items-center h-28 bg-paper-soft/20 border border-dashed border-line">
                      <span className="tracking-wordmark font-medium text-sm text-ink">
                        U · P · A · S · S
                      </span>
                    </div>
                  </div>
                  <div>
                    <p className="text-xs text-ink-70 mb-4 leading-relaxed">
                      Dạng chữ ngang cách đều (spaced letter) đại diện cho phong cách thiết kế in ấn hiện đại. Thích hợp dùng trên Header/Footer.
                    </p>
                    <button
                      onClick={() => handleCopy('wordmark', LOGO_SVGS.wordmark)}
                      className="w-full text-center py-2.5 bg-paper hover:bg-moss hover:text-paper border border-line text-xs font-semibold tracking-label transition-colors"
                    >
                      {copiedId === 'wordmark' ? 'ĐÃ SAO CHÉP MÃ! ✓' : 'SAO CHÉP MÃ HTML'}
                    </button>
                  </div>
                </div>
              </ScrollReveal>

              {/* Display Lockup */}
              <ScrollReveal delay={0.3}>
                <div className="border border-line bg-snow p-8 flex flex-col h-full justify-between card-shadow">
                  <div>
                    <span className="text-xs font-mono text-ink-50 font-semibold uppercase tracking-wider">03. Display Logo</span>
                    <div className="my-8 flex justify-center items-center h-28 bg-ink text-paper p-4">
                      <Logo variant="display" size="md" href={null} monochrome={false} className="text-paper" />
                    </div>
                  </div>
                  <div>
                    <p className="text-xs text-paper-soft/80 bg-ink p-3 rounded mb-4 leading-relaxed font-mono text-[10px]">
                      U &lt;span className="text-moss"&gt;^&lt;/span&gt; PASS
                    </p>
                    <button
                      onClick={() => handleCopy('display', LOGO_SVGS.display)}
                      className="w-full text-center py-2.5 bg-paper hover:bg-moss hover:text-paper border border-line text-xs font-semibold tracking-label transition-colors"
                    >
                      {copiedId === 'display' ? 'ĐÃ SAO CHÉP MÃ! ✓' : 'SAO CHÉP MÃ HTML'}
                    </button>
                  </div>
                </div>
              </ScrollReveal>
            </div>
          </div>
        </section>

        {/* ─── (04) Bảng Màu (Color Palette) ────────────────── */}
        <section className="border-b border-line bg-paper-soft/20">
          <div className="max-w-7xl mx-auto px-6 sm:px-10 py-16 sm:py-24">
            <ScrollReveal>
              <SectionNumber n={4} label="Bảng màu" />
              <h2 className="font-display text-3xl sm:text-4xl text-ink mt-4 mb-4">
                Hệ sắc độ <em className="italic">nhãn nhặn, dịu mát</em>.
              </h2>
              <p className="text-sm text-ink-70 max-w-2xl mb-12">
                Bảng màu được căn chỉnh độ bão hòa thấp để mô phỏng trang giấy. Nhấp vào các thẻ màu dưới đây để sao chép mã màu HEX.
              </p>
            </ScrollReveal>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {COLORS.map((color, i) => (
                <ScrollReveal key={color.name} delay={i * 0.05}>
                  <div
                    onClick={() => handleCopy(color.variable, color.hex)}
                    className="border border-line bg-snow p-5 flex flex-col justify-between cursor-pointer hover:border-ink transition-all group card-shadow"
                  >
                    <div>
                      <div className={`h-24 w-full ${color.bg} border ${color.border} flex items-end p-3 justify-between`}>
                        <span className={`text-[10px] font-mono font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-snow text-ink border border-line`}>
                          {color.hex}
                        </span>
                      </div>
                      <h3 className="font-display text-lg text-ink font-semibold mt-4">{color.name}</h3>
                      <p className="mt-2 text-xs text-ink-50 font-mono">{color.variable}</p>
                    </div>
                    <div className="mt-4 pt-4 border-t border-line-soft">
                      <p className="text-xs text-ink-70 leading-relaxed h-12 overflow-hidden">
                        {color.desc}
                      </p>
                      <div className="mt-3 text-right text-[10px] font-semibold text-moss tracking-wider group-hover:underline">
                        {copiedId === color.variable ? 'ĐÃ SAO CHÉP! ✓' : 'NHẤP ĐỂ COPY HEX'}
                      </div>
                    </div>
                  </div>
                </ScrollReveal>
              ))}
            </div>
          </div>
        </section>

        {/* ─── (05) Typography ──────────────────────────────── */}
        <section className="border-b border-line">
          <div className="max-w-7xl mx-auto px-6 sm:px-10 py-16 sm:py-24">
            <div className="grid grid-cols-12 gap-8">
              <div className="col-span-12 md:col-span-4">
                <ScrollReveal>
                  <SectionNumber n={5} label="Chữ viết" />
                  <h2 className="font-display text-3xl sm:text-4xl text-ink mt-4">
                    Quy chuẩn <em className="italic">Typography</em>.
                  </h2>
                  <p className="text-xs text-ink-50 mt-4 leading-relaxed font-sans">
                    Sự kết hợp giữa nghệ thuật cổ điển của font Serif và tính khoa học, rõ ràng của font Sans/Mono.
                  </p>
                </ScrollReveal>
              </div>

              <div className="col-span-12 md:col-span-8 space-y-12">
                {/* Serif */}
                <ScrollReveal>
                  <div className="border-b border-line pb-8">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono text-ink-50 uppercase tracking-wider">Font Tiêu đề (Serif)</span>
                      <span className="text-xs font-mono font-semibold text-moss">Playfair Display</span>
                    </div>
                    <p className="mt-4 font-display text-5xl sm:text-6xl text-ink leading-tight">
                      Chinh phục kỳ thi <em className="italic text-moss font-display">THPT Quốc Gia</em> bằng cách khác biệt.
                    </p>
                    <p className="mt-4 text-xs text-ink-50">
                      Sử dụng cho các tiêu đề lớn, phần dẫn dắt mang tính truyền tải cảm hứng, câu hỏi quan trọng.
                    </p>
                  </div>
                </ScrollReveal>

                {/* Sans */}
                <ScrollReveal>
                  <div className="border-b border-line pb-8">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono text-ink-50 uppercase tracking-wider">Font Nội dung (Sans)</span>
                      <span className="text-xs font-mono font-semibold text-moss">Geist Sans</span>
                    </div>
                    <p className="mt-4 font-sans text-base sm:text-lg text-ink leading-relaxed">
                      Luyện tập với hàng nghìn câu hỏi trắc nghiệm được phân loại chuẩn hóa theo cấu trúc của Bộ Giáo dục & Đào tạo. 
                      Hệ thống tự động theo dõi và phân tích năng lực chi tiết cho từng môn học.
                    </p>
                    <p className="mt-4 text-xs text-ink-50">
                      Sử dụng cho văn bản chính, nội dung câu hỏi trắc nghiệm, các nút bấm và mô tả chung.
                    </p>
                  </div>
                </ScrollReveal>

                {/* Mono */}
                <ScrollReveal>
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono text-ink-50 uppercase tracking-wider">Font Thông số (Mono)</span>
                      <span className="text-xs font-mono font-semibold text-moss">Geist Mono</span>
                    </div>
                    <div className="mt-4 font-mono text-sm sm:text-base text-ink space-y-2 bg-paper-soft/40 p-4 border border-line">
                      <p>Time Left: 00:45:12</p>
                      <p>Success Rate: 84.5% (42/50 questions)</p>
                      <p>Session ID: upass_anal_78a1bc490f23</p>
                    </div>
                    <p className="mt-4 text-xs text-ink-50">
                      Sử dụng cho đồng hồ đếm ngược, mã đề, số câu đúng/sai, số trang, nhãn phụ khoa học.
                    </p>
                  </div>
                </ScrollReveal>
              </div>
            </div>
          </div>
        </section>

        {/* ─── (06) Mascot Spotlight ────────────────────────── */}
        <section className="bg-paper-soft/30">
          <div className="max-w-7xl mx-auto px-6 sm:px-10 py-16 sm:py-24">
            <div className="grid grid-cols-12 gap-8 items-center">
              <div className="col-span-12 md:col-span-5 flex justify-center">
                <ScrollReveal>
                  <div className="relative p-10 bg-snow border border-line rounded-3xl card-shadow flex justify-center items-center">
                    <div className="absolute top-4 left-6 text-[10px] font-mono text-ink-30 uppercase tracking-wider">
                      U-PASS MASCOT v1.0
                    </div>
                    <CustomOwlSVG size={160} />
                  </div>
                </ScrollReveal>
              </div>

              <div className="col-span-12 md:col-span-7 md:pl-8">
                <ScrollReveal delay={0.1}>
                  <SectionNumber n={6} label="Linh vật học thuật" />
                  <h2 className="font-display text-4xl text-ink mt-4 mb-6">
                    Gặp gỡ <em className="italic">Cú Mèo U-PASS</em>
                  </h2>
                  <p className="text-sm sm:text-base text-ink-70 leading-relaxed font-sans mb-6">
                    Được phác họa bằng những đường nét tối giản của trường phái Line-art, chú Cú Mèo U-PASS hiện lên 
                    với chiếc kính cận tri thức và chiếc mũ cử nhân. Không chỉ là một hình ảnh trang trí, Cú Mèo là 
                    hiện thân của một người gia sư thông thái, tận tụy và biết lắng nghe sĩ tử.
                  </p>
                  <div className="border-l-2 border-moss pl-4 py-1 italic text-xs text-ink-50 font-sans">
                    "Chào sĩ tử! Cú Mèo luôn túc trực góc phải màn hình để hướng dẫn bạn phân tích cấu trúc câu hỏi, giải thích chi tiết LaTeX và gợi ý phương án ôn luyện phù hợp nhất."
                  </div>
                </ScrollReveal>
              </div>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </>
  )
}
