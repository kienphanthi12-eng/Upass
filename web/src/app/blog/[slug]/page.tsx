import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import Header from '@/components/Header'
import Footer from '@/components/Footer'
import DisplayHeading from '@/components/ui/DisplayHeading'
import SectionNumber from '@/components/ui/SectionNumber'
import ScrollReveal from '@/components/ui/ScrollReveal'
import { blogPosts } from '@/data/blog'

interface PageProps {
  params: Promise<{ slug: string }>
}

// Generate dynamic metadata for SEO crawlers
export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params
  const post = blogPosts.find((p) => p.slug === slug)
  if (!post) return { title: 'Không tìm thấy bài viết' }

  return {
    title: `${post.seoTitle} | U-PASS Blog`,
    description: post.description,
    keywords: post.keywords.join(', '),
  }
}

// Pre-render blog posts as static HTML pages during build (SSG)
export async function generateStaticParams() {
  return blogPosts.map((post) => ({
    slug: post.slug,
  }))
}

// Helper to render inline markdown styles like bold (**) and inline code (`)
function parseInlineStyles(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = []
  let key = 0

  // Regex to split by bold **bold** or code `code`
  const regex = /(\*\*.*?\*\*|`.*?`)/g
  const tokens = text.split(regex)

  for (const token of tokens) {
    if (token.startsWith('**') && token.endsWith('**')) {
      parts.push(
        <strong key={key++} className="font-semibold text-ink">
          {token.slice(2, -2)}
        </strong>
      )
    } else if (token.startsWith('`') && token.endsWith('`')) {
      parts.push(
        <code key={key++} className="font-mono text-xs px-1.5 py-0.5 bg-paper-soft text-moss border border-line-soft rounded">
          {token.slice(1, -1)}
        </code>
      )
    } else {
      parts.push(token)
    }
  }

  return parts
}

// Helper to render simple Markdown headings, lists, blockquotes and paragraphs to JSX
function renderMarkdown(content: string) {
  const lines = content.split('\n')
  const elements: React.ReactNode[] = []

  let key = 0
  let listItems: string[] = []

  const flushList = () => {
    if (listItems.length > 0) {
      elements.push(
        <ul key={`list-${key++}`} className="list-disc pl-6 mb-6 text-ink-70 space-y-2 font-sans text-base">
          {listItems.map((item, idx) => (
            <li key={idx}>{parseInlineStyles(item)}</li>
          ))}
        </ul>
      )
      listItems = []
    }
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()

    if (line.startsWith('## ')) {
      flushList()
      elements.push(
        <h2 key={key++} className="font-display text-2xl sm:text-3xl text-ink mt-10 mb-4 font-semibold leading-tight">
          {parseInlineStyles(line.replace('## ', ''))}
        </h2>
      )
    } else if (line.startsWith('### ')) {
      flushList()
      elements.push(
        <h3 key={key++} className="font-display text-xl sm:text-2xl text-ink mt-8 mb-3 font-semibold leading-tight">
          {parseInlineStyles(line.replace('### ', ''))}
        </h3>
      )
    } else if (line.startsWith('#### ')) {
      flushList()
      elements.push(
        <h4 key={key++} className="font-display text-lg sm:text-xl text-ink mt-6 mb-2 font-semibold leading-tight">
          {parseInlineStyles(line.replace('#### ', ''))}
        </h4>
      )
    } else if (line.startsWith('* ') || line.startsWith('- ')) {
      const cleanLine = line.replace(/^[\*\-]\s+/, '')
      listItems.push(cleanLine)
    } else if (line.startsWith('> ')) {
      flushList()
      elements.push(
        <blockquote key={key++} className="border-l-2 border-moss pl-4 py-1.5 italic text-ink-50 bg-moss-bg/10 pr-4 my-6 text-sm sm:text-base">
          {parseInlineStyles(line.replace('> ', ''))}
        </blockquote>
      )
    } else if (line === '') {
      flushList()
    } else {
      flushList()
      // Normal paragraph
      elements.push(
        <p key={key++} className="font-sans text-ink-70 leading-relaxed text-base mb-6">
          {parseInlineStyles(line)}
        </p>
      )
    }
  }
  flushList()
  return elements
}

export default async function BlogPostDetailPage({ params }: PageProps) {
  const { slug } = await params
  const post = blogPosts.find((p) => p.slug === slug)

  if (!post) {
    notFound()
  }

  return (
    <>
      <Header />

      <main className="min-h-screen bg-paper pb-24">
        {/* Article Header */}
        <article className="max-w-4xl mx-auto px-6 sm:px-10 py-16 sm:py-24">
          <ScrollReveal>
            <div className="flex items-center gap-3 text-xs font-mono text-ink-50 mb-6">
              <Link href="/blog" className="hover:text-moss hover:underline">
                BLOG
              </Link>
              <span>/</span>
              <span className="uppercase text-moss font-semibold">{post.category}</span>
              <span>/</span>
              <span>{post.date}</span>
            </div>
          </ScrollReveal>

          <ScrollReveal delay={0.1}>
            <DisplayHeading size="lg" as="h1" className="leading-tight mb-8">
              {post.title}
            </DisplayHeading>
          </ScrollReveal>

          <div className="h-px bg-line my-8" />

          {/* Article Body Content */}
          <ScrollReveal delay={0.2}>
            <div className="prose max-w-none text-ink-70">
              {renderMarkdown(post.content)}
            </div>
          </ScrollReveal>

          <div className="h-px bg-line my-12" />

          {/* CTA / Promotion Section */}
          <ScrollReveal delay={0.3}>
            <div className="bg-snow border border-line p-8 card-shadow flex flex-col sm:flex-row items-center justify-between gap-6">
              <div>
                <h4 className="font-display text-xl sm:text-2xl text-ink font-semibold mb-2">
                  Trải nghiệm học tập tĩnh lặng cùng U-PASS
                </h4>
                <p className="text-xs sm:text-sm text-ink-70 font-sans">
                  Luyện đề thi THPT chuẩn hóa không quảng cáo, tối ưu điểm số với Trợ lý AI Cú Mèo ngay hôm nay.
                </p>
              </div>
              <Link
                href="/register"
                className="shrink-0 px-6 py-3 bg-ink text-paper hover:bg-moss hover:text-paper text-xs font-semibold tracking-label transition-colors"
              >
                ĐĂNG KÝ MIỄN PHÍ →
              </Link>
            </div>
          </ScrollReveal>

          {/* Back button */}
          <div className="mt-12 text-center">
            <Link
              href="/blog"
              className="text-xs font-semibold tracking-label text-ink-50 hover:text-ink link-editorial"
            >
              ← QUAY LẠI DANH SÁCH BÀI VIẾT
            </Link>
          </div>
        </article>
      </main>

      <Footer />
    </>
  )
}
