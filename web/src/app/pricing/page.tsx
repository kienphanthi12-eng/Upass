'use client'

import { useState } from 'react'
import Header from '@/components/Header'
import Footer from '@/components/Footer'
import SectionNumber from '@/components/ui/SectionNumber'
import DisplayHeading from '@/components/ui/DisplayHeading'
import ScrollReveal from '@/components/ui/ScrollReveal'
import { motion, AnimatePresence } from 'motion/react'
import { Check, MessageSquare, Phone, Copy, CheckCircle2 } from 'lucide-react'

interface PricingPlan {
  id: string
  name: string
  price: string
  period: string
  description: string
  features: string[]
  isPopular?: boolean
  ctaText: string
  zaloMessage: string
}

const STUDENT_PLANS: PricingPlan[] = [
  {
    id: 'student-free',
    name: 'Cơ bản',
    price: '0đ',
    period: 'Miễn phí',
    description: 'Dành cho học sinh làm quen với hệ thống và thi thử cơ bản.',
    features: [
      'Xem danh sách đề thi công khai',
      'Làm bài thi thử trực tuyến cơ bản',
      'Xem kết quả và thống kê bài thi vừa làm',
      'Luyện tập giới hạn một số chủ đề chính',
    ],
    ctaText: 'Trải nghiệm ngay',
    zaloMessage: 'Chào U-PASS, mình muốn tìm hiểu thêm về tài khoản Học sinh.',
  },
  {
    id: 'student-premium',
    name: 'U-PASS Premium',
    price: '99.000đ',
    period: 'tháng',
    description: 'Mở khóa toàn bộ tính năng và kho dữ liệu để ôn tập tối đa.',
    features: [
      'Mở khóa 5.000+ đề thi THPT QG tất cả các môn',
      'Xem giải thích và lời giải chi tiết (Phần 1, 2, 3 tự luận)',
      'Luyện tập tự do không giới hạn chủ đề & mức độ',
      'Thống kê chi tiết, phân tích điểm số & tiến trình tiến bộ',
      'Không quảng cáo, giao diện học tập tối giản',
    ],
    isPopular: true,
    ctaText: 'Nâng cấp Premium',
    zaloMessage: 'Chào U-PASS, mình muốn nâng cấp tài khoản Học sinh Premium.',
  },
  {
    id: 'student-yearly',
    name: 'Premium Năm học',
    price: '299.000đ',
    period: 'năm học (9 tháng)',
    description: 'Lựa chọn tiết kiệm nhất cho cả năm học lớp 12.',
    features: [
      'Đầy đủ tính năng như gói Premium tháng',
      'Tiết kiệm hơn 65% so với mua lẻ từng tháng',
      'Kích hoạt một lần dùng suốt cả năm học',
      'Tặng kèm tài liệu tổng ôn thi THPT QG độc quyền',
    ],
    ctaText: 'Đăng ký trọn gói',
    zaloMessage: 'Chào U-PASS, mình muốn đăng ký gói Học sinh Premium Năm học.',
  },
]

const TEACHER_PLANS: PricingPlan[] = [
  {
    id: 'teacher-free',
    name: 'Cơ bản',
    price: '0đ',
    period: 'Miễn phí',
    description: 'Dành cho giáo viên trải nghiệm tạo lớp học trực tuyến.',
    features: [
      'Tạo tối đa 2 lớp học ảo',
      'Quản lý tối đa 30 học sinh',
      'Nhập thủ công tối đa 3 đề thi trực tuyến',
      'Xem bảng điểm cơ bản của học sinh',
    ],
    ctaText: 'Sử dụng miễn phí',
    zaloMessage: 'Chào U-PASS, tôi muốn đăng ký tài khoản Giáo viên trải nghiệm.',
  },
  {
    id: 'teacher-pro',
    name: 'Giáo viên Pro',
    price: '199.000đ',
    period: 'tháng',
    description: 'Giải pháp toàn diện tối ưu hóa việc biên soạn và giảng dạy.',
    features: [
      'Không giới hạn số lớp học & học sinh',
      'Công cụ AI OCR quét ảnh/PDF đề thi thành Markdown toán học',
      'Tạo ma trận đề thi & tự động sinh đề từ ngân hàng câu hỏi',
      'Thống kê phổ điểm chi tiết, xuất bảng điểm Excel tự động',
      'Tự định cấu hình thời gian & giao diện thi cho học sinh',
      'Hỗ trợ ưu tiên 24/7 trực tiếp qua điện thoại / Zalo',
    ],
    isPopular: true,
    ctaText: 'Nâng cấp Pro',
    zaloMessage: 'Chào U-PASS, tôi muốn nâng cấp tài khoản Giáo viên Pro.',
  },
  {
    id: 'teacher-yearly',
    name: 'Pro Năm học',
    price: '799.000đ',
    period: 'năm',
    description: 'Đồng hành cùng giáo viên trong cả năm giảng dạy và ra đề.',
    features: [
      'Đầy đủ tính năng như gói Giáo viên Pro tháng',
      'Tiết kiệm hơn 65% chi phí hàng năm',
      'Kích hoạt nhanh chóng, hoạt động ổn định trọn năm học',
      'Được hỗ trợ tùy biến giao diện riêng cho các kỳ thi lớn của lớp',
    ],
    ctaText: 'Đăng ký trọn năm',
    zaloMessage: 'Chào U-PASS, tôi muốn đăng ký gói Giáo viên Pro Năm học.',
  },
]

export default function PricingPage() {
  const [role, setRole] = useState<'student' | 'teacher'>('student')
  const [selectedPlan, setSelectedPlan] = useState<PricingPlan | null>(null)
  const [copied, setCopied] = useState(false)

  const plans = role === 'student' ? STUDENT_PLANS : TEACHER_PLANS

  const handleCopyPhone = () => {
    navigator.clipboard.writeText('0868508968')
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleOpenContact = (plan: PricingPlan) => {
    setSelectedPlan(plan)
  }

  return (
    <div className="flex flex-col min-h-screen">
      <Header />

      <main className="flex-1">
        {/* Hero Section */}
        <section className="max-w-7xl mx-auto px-6 sm:px-10 pt-16 sm:pt-24 pb-12">
          <ScrollReveal>
            <SectionNumber n={1} label="Bảng giá & Dịch vụ" />
          </ScrollReveal>
          <ScrollReveal delay={0.08}>
            <DisplayHeading size="xl" className="mt-6 max-w-4xl">
              Nâng tầm <em className="italic">học tập</em> & <em className="italic">giảng dạy</em>.
            </DisplayHeading>
          </ScrollReveal>
          <ScrollReveal delay={0.15}>
            <p className="mt-6 text-base sm:text-lg text-ink-50 max-w-2xl leading-relaxed">
              U-PASS cung cấp các gói dịch vụ tối ưu giúp mở khóa toàn bộ đề thi, lời giải chi tiết và công cụ hỗ trợ AI OCR cao cấp dành riêng cho giáo viên.
            </p>
          </ScrollReveal>

          {/* Toggle Role Switcher */}
          <ScrollReveal delay={0.2} className="mt-12 flex justify-center">
            <div className="relative flex p-1 bg-paper-soft border border-line rounded-none">
              <button
                onClick={() => setRole('student')}
                className={`relative px-6 py-2.5 text-xs sm:text-sm tracking-label transition-colors duration-300 z-10 font-medium ${
                  role === 'student' ? 'text-paper' : 'text-ink-50 hover:text-ink'
                }`}
              >
                Dành cho Học sinh
              </button>
              <button
                onClick={() => setRole('teacher')}
                className={`relative px-6 py-2.5 text-xs sm:text-sm tracking-label transition-colors duration-300 z-10 font-medium ${
                  role === 'teacher' ? 'text-paper' : 'text-ink-50 hover:text-ink'
                }`}
              >
                Dành cho Giáo viên
              </button>

              {/* Sliding background */}
              <motion.div
                className="absolute inset-y-1 bg-ink"
                initial={false}
                animate={{
                  left: role === 'student' ? '4px' : '50%',
                  width: 'calc(50% - 4px)',
                }}
                transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              />
            </div>
          </ScrollReveal>
        </section>

        {/* Pricing Cards */}
        <section className="border-t border-line bg-paper-soft/40 py-16 sm:py-24">
          <div className="max-w-7xl mx-auto px-6 sm:px-10">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-stretch">
              {plans.map((plan, idx) => (
                <ScrollReveal
                  key={plan.id}
                  delay={idx * 0.1}
                  className="flex"
                >
                  <div
                    className={`flex flex-col w-full p-8 border bg-paper transition-all duration-300 relative group ${
                      plan.isPopular
                        ? 'border-moss ring-1 ring-moss card-shadow'
                        : 'border-line hover:border-ink'
                    }`}
                  >
                    {plan.isPopular && (
                      <span className="absolute top-0 right-8 -translate-y-1/2 bg-moss text-paper text-[10px] tracking-label font-mono px-3 py-1 font-semibold uppercase">
                        Khuyên dùng
                      </span>
                    )}

                    <div className="mb-6">
                      <h3 className="font-display text-2xl text-ink font-semibold">
                        {plan.name}
                      </h3>
                      <p className="mt-2 text-xs text-ink-50 min-h-8">
                        {plan.description}
                      </p>
                    </div>

                    <div className="mb-8 flex items-baseline gap-1.5 border-b border-line pb-6">
                      <span className="font-display text-5xl font-normal text-ink">
                        {plan.price}
                      </span>
                      {plan.price !== '0đ' && (
                        <span className="text-xs tracking-label text-ink-50 font-mono">
                          / {plan.period}
                        </span>
                      )}
                    </div>

                    {/* Features List */}
                    <ul className="space-y-4 mb-10 flex-1">
                      {plan.features.map((feature, fIdx) => (
                        <li key={fIdx} className="flex items-start gap-3">
                          <Check size={16} className="text-moss shrink-0 mt-0.5" />
                          <span className="text-sm text-ink-70 leading-normal">
                            {feature}
                          </span>
                        </li>
                      ))}
                    </ul>

                    {/* CTA Button */}
                    <button
                      onClick={() => handleOpenContact(plan)}
                      className={`w-full py-3.5 text-xs sm:text-sm tracking-label font-medium transition-colors text-center ${
                        plan.isPopular
                          ? 'bg-moss text-paper hover:bg-ink'
                          : 'border border-line text-ink hover:border-ink hover:bg-paper-soft'
                      }`}
                    >
                      {plan.ctaText} →
                    </button>
                  </div>
                </ScrollReveal>
              ))}
            </div>
          </div>
        </section>

        {/* Dynamic QA Section */}
        <section className="border-t border-line py-16 sm:py-24">
          <div className="max-w-4xl mx-auto px-6 sm:px-10">
            <SectionNumber n={2} label="Câu hỏi thường gặp" className="mb-10" />
            <div className="space-y-8">
              {[
                {
                  q: 'Sau khi thanh toán làm thế nào để được mở khóa quyền?',
                  a: 'Khi bạn liên hệ qua Zalo và hoàn tất chuyển khoản theo gói cước, Quản trị viên của U-PASS sẽ ngay lập tức đối chiếu tên tài khoản email của bạn trên hệ thống và cấp quyền Premium hoặc Giáo viên Pro trực tiếp qua trang quản trị. Thời gian kích hoạt chỉ từ 2 đến 5 phút.',
                },
                {
                  q: 'Tôi có thể dùng thử công cụ AI OCR của giáo viên không?',
                  a: 'Có. Giáo viên có thể đăng ký tài khoản và trải nghiệm công cụ quét đề thi mẫu. Tuy nhiên để xử lý toàn bộ các trang tài liệu PDF dài hoặc ảnh chụp thực tế có công thức toán phức tạp, bạn nên nâng cấp lên gói Giáo viên Pro để đảm bảo hiệu suất AI cao nhất.',
                },
                {
                  q: 'Gói năm học được tính thời gian như thế nào?',
                  a: 'Gói năm học dành cho học sinh kéo dài trong 9 tháng học (từ lúc kích hoạt đến hết mùa thi THPT Quốc Gia). Gói năm học của giáo viên kéo dài trọn vẹn 12 tháng kể từ ngày kích hoạt.',
                },
              ].map((faq, idx) => (
                <div key={idx} className="border-b border-line pb-6">
                  <h4 className="font-display text-xl text-ink font-semibold">
                    {faq.q}
                  </h4>
                  <p className="mt-3 text-sm text-ink-50 leading-relaxed">
                    {faq.a}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>

      {/* Payment / Contact Zalo Modal */}
      <AnimatePresence>
        {selectedPlan && (
          <div
            className="fixed inset-0 bg-ink/40 backdrop-blur-sm flex items-center justify-center z-50 p-4 overflow-y-auto"
            onClick={() => setSelectedPlan(null)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.25, ease: 'easeOut' }}
              className="bg-paper border border-line p-8 max-w-md w-full relative card-shadow my-8"
              onClick={e => e.stopPropagation()}
            >
              {/* Close Button */}
              <button
                onClick={() => setSelectedPlan(null)}
                className="absolute top-4 right-4 text-ink-30 hover:text-ink text-xl transition-colors font-mono"
              >
                ×
              </button>

              <p className="text-xs tracking-label text-ink-50 mb-3">Thông tin kích hoạt</p>
              <h3 className="font-display text-3xl text-ink mb-2">
                Đăng ký <em className="italic">{selectedPlan.name}</em>
              </h3>
              <p className="text-sm text-ink-50 mb-6">
                Bạn đã chọn gói cước trị giá <strong className="text-ink">{selectedPlan.price}</strong>. Vui lòng liên hệ qua Zalo của Quản trị viên để kích hoạt tài khoản của bạn.
              </p>

              {/* Zalo Info Card */}
              <div className="bg-paper-soft border border-line p-5 mb-6 space-y-4">
                <div className="flex items-center gap-3">
                  <MessageSquare size={18} className="text-moss" />
                  <div>
                    <p className="text-xs text-ink-50">Zalo Hỗ trợ trực tiếp</p>
                    <p className="text-base text-ink font-semibold">Phan Trung Kiên</p>
                  </div>
                </div>

                <div className="flex items-center justify-between gap-3 border-t border-line/50 pt-3">
                  <div className="flex items-center gap-3">
                    <Phone size={18} className="text-moss" />
                    <div>
                      <p className="text-xs text-ink-50">Số điện thoại Zalo</p>
                      <p className="text-base text-ink font-mono font-semibold">0868 508 968</p>
                    </div>
                  </div>
                  <button
                    onClick={handleCopyPhone}
                    className="flex items-center gap-1.5 text-xs text-moss hover:text-ink transition-colors px-2.5 py-1.5 border border-moss/20 hover:border-ink bg-paper"
                  >
                    {copied ? <CheckCircle2 size={12} /> : <Copy size={12} />}
                    {copied ? 'Đã sao chép' : 'Sao chép'}
                  </button>
                </div>
              </div>

              {/* Pre-written message hint */}
              <div className="mb-6">
                <p className="text-xs text-ink-50 mb-2">Lời nhắn mẫu khi liên hệ Zalo:</p>
                <div className="p-3 bg-paper border border-line text-xs text-ink-70 italic leading-relaxed">
                  &quot;{selectedPlan.zaloMessage}&quot;
                </div>
              </div>

              {/* QR and Quick Chat Link */}
              <div className="flex flex-col gap-3">
                <a
                  href={`https://zalo.me/0868508968?text=${encodeURIComponent(selectedPlan.zaloMessage)}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full py-3.5 bg-ink text-paper hover:bg-moss text-xs tracking-label font-medium transition-colors text-center inline-flex items-center justify-center gap-2"
                >
                  <MessageSquare size={14} />
                  Nhắn Zalo Kích Hoạt Ngay →
                </a>
                <button
                  onClick={() => setSelectedPlan(null)}
                  className="w-full py-3 text-xs tracking-label text-ink-50 hover:text-ink transition-colors text-center"
                >
                  Đóng cửa sổ
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      <Footer />
    </div>
  )
}
