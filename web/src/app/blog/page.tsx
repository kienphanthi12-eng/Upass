'use client'

import { useState } from 'react'
import Link from 'next/link'
import Header from '@/components/Header'
import Footer from '@/components/Footer'
import DisplayHeading from '@/components/ui/DisplayHeading'
import SectionNumber from '@/components/ui/SectionNumber'
import ScrollReveal from '@/components/ui/ScrollReveal'
import { blogPosts } from '@/data/blog'

export default function BlogListPage() {
  const [selectedCategory, setSelectedCategory] = useState<string>('All')
  const [searchQuery, setSearchQuery] = useState<string>('')

  const categories = ['All', 'Học sinh & Phụ huynh', 'Giáo viên & Trường học']

  // Filter posts
  const filteredPosts = blogPosts.filter((post) => {
    const matchesCategory = selectedCategory === 'All' || post.category === selectedCategory
    const matchesSearch =
      post.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      post.description.toLowerCase().includes(searchQuery.toLowerCase())
    return matchesCategory && matchesSearch
  })

  // Feature post is the first one in the filtered list
  const featuredPost = filteredPosts[0]
  const otherPosts = filteredPosts.slice(1)

  return (
    <>
      <Header />

      <main className="min-h-screen bg-paper pb-24">
        {/* Hero Section */}
        <section className="border-b border-line">
          <div className="max-w-7xl mx-auto px-6 sm:px-10 py-16 sm:py-24">
            <ScrollReveal>
              <SectionNumber n={1} label="Knowledge Hub" />
            </ScrollReveal>

            <ScrollReveal delay={0.1}>
              <DisplayHeading size="xl" className="mt-6 max-w-4xl">
                Góc nhìn <em className="italic font-display text-moss">Tri Thức</em> & Công Nghệ
              </DisplayHeading>
            </ScrollReveal>

            <ScrollReveal delay={0.2}>
              <div className="mt-8 max-w-2xl">
                <p className="text-lg text-ink-70 leading-relaxed font-sans">
                  Nơi chia sẻ các bài viết phân tích chuyên sâu về xu hướng giáo dục tốt nghiệp THPT mới, 
                  phương pháp tự học thông minh và giải pháp chuyển đổi số lớp học bằng EdTech.
                </p>
              </div>
            </ScrollReveal>
          </div>
        </section>

        {/* Filter Section */}
        <section className="border-b border-line bg-paper-soft/30 sticky top-16 sm:top-20 z-10 backdrop-blur-md">
          <div className="max-w-7xl mx-auto px-6 sm:px-10 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            {/* Category Buttons */}
            <div className="flex flex-wrap gap-2">
              {categories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  className={`px-4 py-2 text-xs tracking-label transition-colors border ${
                    selectedCategory === cat
                      ? 'bg-ink text-paper border-ink'
                      : 'bg-transparent text-ink-50 border-line hover:text-ink hover:border-ink'
                  }`}
                >
                  {cat === 'All' ? 'TẤT CẢ BÀI VIẾT' : cat.toUpperCase()}
                </button>
              ))}
            </div>

            {/* Search Input */}
            <div className="relative max-w-xs w-full">
              <input
                type="text"
                placeholder="Tìm kiếm bài viết..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full px-4 py-2 text-xs font-sans bg-transparent border border-line text-ink placeholder:text-ink-30 focus:outline-none focus:border-moss"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-3 top-2.5 text-xs text-ink-50 hover:text-ink"
                >
                  ✕
                </button>
              )}
            </div>
          </div>
        </section>

        {/* Blog Post List Grid */}
        <section className="max-w-7xl mx-auto px-6 sm:px-10 py-12">
          {filteredPosts.length === 0 ? (
            <div className="text-center py-20">
              <p className="font-display text-2xl text-ink-50 italic">Không tìm thấy bài viết nào phù hợp.</p>
            </div>
          ) : (
            <div className="space-y-16">
              {/* Featured Post (only when not searching / filtering too strictly) */}
              {featuredPost && searchQuery === '' && (
                <ScrollReveal>
                  <div className="border border-line bg-snow p-6 sm:p-10 card-shadow hover:border-moss transition-colors group">
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
                      <div className="lg:col-span-7 flex flex-col justify-between h-full">
                        <div>
                          <div className="flex items-center gap-3 text-xs font-mono text-ink-50 mb-4">
                            <span className="uppercase tracking-wider px-2.5 py-0.5 bg-moss-bg text-moss font-semibold">
                              {featuredPost.category}
                            </span>
                            <span>•</span>
                            <span>{featuredPost.date}</span>
                          </div>
                          
                          <Link href={`/blog/${featuredPost.slug}`}>
                            <h2 className="font-display text-3xl sm:text-4xl lg:text-5xl text-ink group-hover:text-moss transition-colors leading-tight mb-4">
                              {featuredPost.title}
                            </h2>
                          </Link>
                          
                          <p className="text-sm sm:text-base text-ink-70 leading-relaxed font-sans mb-6 line-clamp-3">
                            {featuredPost.description}
                          </p>
                        </div>

                        <div>
                          <Link
                            href={`/blog/${featuredPost.slug}`}
                            className="inline-flex items-center gap-2 text-xs font-semibold tracking-label text-moss group-hover:underline"
                          >
                            ĐỌC CHI TIẾT <span className="group-hover:translate-x-1 transition-transform">→</span>
                          </Link>
                        </div>
                      </div>
                      
                      {/* Brand decorative side panel for featured post */}
                      <div className="lg:col-span-5 hidden lg:flex bg-paper-soft border border-line h-64 items-center justify-center relative overflow-hidden select-none">
                        <div className="absolute inset-0 border border-line/20 opacity-30 grid grid-cols-4 pointer-events-none">
                          <div className="border-r border-line/30"></div>
                          <div className="border-r border-line/30"></div>
                          <div className="border-r border-line/30"></div>
                        </div>
                        <span className="font-display italic text-8xl text-line/80 font-bold">U-PASS</span>
                      </div>
                    </div>
                  </div>
                </ScrollReveal>
              )}

              {/* Grid of Other Posts */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                {(searchQuery !== '' ? filteredPosts : otherPosts).map((post, i) => (
                  <ScrollReveal key={post.slug} delay={i * 0.05}>
                    <div className="border border-line bg-snow p-6 card-shadow flex flex-col justify-between h-full hover:border-moss transition-colors group">
                      <div>
                        <div className="flex items-center gap-2 text-[10px] font-mono text-ink-50 mb-3">
                          <span className="uppercase tracking-wider font-semibold text-moss">
                            {post.category}
                          </span>
                          <span>•</span>
                          <span>{post.date}</span>
                        </div>

                        <Link href={`/blog/${post.slug}`}>
                          <h3 className="font-display text-xl sm:text-2xl text-ink group-hover:text-moss transition-colors leading-tight mb-3 line-clamp-2">
                            {post.title}
                          </h3>
                        </Link>

                        <p className="text-xs text-ink-70 leading-relaxed font-sans line-clamp-3 mb-6">
                          {post.description}
                        </p>
                      </div>

                      <div className="pt-4 border-t border-line-soft">
                        <Link
                          href={`/blog/${post.slug}`}
                          className="inline-flex items-center gap-1.5 text-[10px] font-semibold tracking-label text-ink group-hover:text-moss group-hover:underline"
                        >
                          ĐỌC BÀI VIẾT <span>→</span>
                        </Link>
                      </div>
                    </div>
                  </ScrollReveal>
                ))}
              </div>
            </div>
          )}
        </section>
      </main>

      <Footer />
    </>
  )
}
