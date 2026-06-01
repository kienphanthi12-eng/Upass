import type { Metadata } from "next";
import { Playfair_Display, Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import OwlChatbot from "@/components/OwlChatbot";
import AnalyticsTracker from "@/components/AnalyticsTracker";


const playfair = Playfair_Display({
  subsets: ["latin", "latin-ext", "vietnamese"],
  style: ["normal", "italic"],
  variable: "--font-playfair",
  display: "swap",
});

const geist = Geist({
  subsets: ["latin", "latin-ext"],
  variable: "--font-geist",
  display: "swap",
});

const geistMono = Geist_Mono({
  subsets: ["latin", "latin-ext"],
  variable: "--font-geist-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "U-PASS — Nền tảng Luyện thi THPT Quốc gia | Tối Giản & Tập Trung",
  description:
    "Hệ thống luyện thi trắc nghiệm THPT Quốc gia không quảng cáo nhiễu. Trải nghiệm học thuật cao cấp với công cụ OCR đề thi chuyên nghiệp và trợ lý AI Cú Mèo giải đáp chi tiết 24/7.",
  keywords:
    "U-PASS, UPASS, luyện thi THPT, trắc nghiệm THPT, đề thi tốt nghiệp, ôn thi đại học, OCR đề thi, giải bài tập bằng AI, toán lý hóa anh thpt",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="vi"
      className={`h-full ${playfair.variable} ${geist.variable} ${geistMono.variable}`}
    >
      <head>
        <link rel="stylesheet" href="/katex.min.css" />
      </head>
      {/* NB: bg-paper is on html (via globals.css) so body::before noise (z-index:-1)
          is visible above html bg but below content. Don't re-add bg on body. */}
      <body className="min-h-full flex flex-col text-ink antialiased">
        {children}
        <OwlChatbot />
        <AnalyticsTracker />
      </body>

    </html>
  );
}
