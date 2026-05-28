import type { Metadata } from "next";
import { Instrument_Serif, Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import OwlChatbot from "@/components/OwlChatbot";
import AnalyticsTracker from "@/components/AnalyticsTracker";


const instrument = Instrument_Serif({
  weight: "400",
  subsets: ["latin", "latin-ext"],
  style: ["normal", "italic"],
  variable: "--font-instrument",
  display: "swap",
});

const geist = Geist({
  subsets: ["latin", "latin-ext"],
  variable: "--font-geist",
  display: "swap",
});

const geistMono = Geist_Mono({
  subsets: ["latin"],
  variable: "--font-geist-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "U-PASS — Nền tảng luyện thi THPT",
  description:
    "Nền tảng luyện thi trắc nghiệm trực tuyến — ôn tập hiệu quả, tự tin bước vào kỳ thi tốt nghiệp THPT.",
  keywords:
    "U-PASS, UPASS, luyện thi THPT, trắc nghiệm, toán, vật lý, hóa học, luyện thi đại học",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="vi"
      className={`h-full ${instrument.variable} ${geist.variable} ${geistMono.variable}`}
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
