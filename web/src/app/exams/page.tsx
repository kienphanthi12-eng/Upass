'use client'

import { useState, useEffect, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import Header from '@/components/Header'
import Footer from '@/components/Footer'
import SectionNumber from '@/components/ui/SectionNumber'
import DisplayHeading from '@/components/ui/DisplayHeading'
import ScrollReveal from '@/components/ui/ScrollReveal'
import { createClient } from '@/lib/supabase'
import type { Exam, Subject } from '@/lib/types'
import { examDisplayName } from '@/lib/types'
import { Search } from 'lucide-react'

const EXAM_TYPE_LABELS: Record<string, string> = {
  THU: 'Đề thi thử',
  thi_thu: 'Đề thi thử',
  THPT_QG: 'THPT Quốc Gia',
  GK: 'Giữa kỳ',
  CK: 'Cuối kỳ',
  KS: 'Khảo sát',
  ON: 'Ôn thi',
  on_thi: 'Ôn thi',
}

// Thứ tự ưu tiên hiển thị môn học
const SUBJECT_ORDER = ['TOAN', 'VAN', 'ANH', 'LY', 'HOA', 'SINH', 'SU', 'DIA', 'GDCD', 'TIN', 'CN']

export default function ExamsPage() {
  const router = useRouter()
  const supabase = createClient()
  const [exams, setExams] = useState<Exam[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [yearFilter, setYearFilter] = useState<number | null>(null)
  const [subjectFilter, setSubjectFilter] = useState<number | null>(null)
  const [years, setYears] = useState<number[]>([])

  useEffect(() => {
    async function load() {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) { router.push('/login'); return }

      const { data } = await supabase
        .from('exams')
        .select(`
          id, title, display_title, year, exam_type, subject_id, total_pages, created_at,
          subjects(id, code, name),
          question_count:questions(count)
        `)
        .eq('ocr_status', 'done')
        .order('id', { ascending: false })
      if (data) {
        const examsData = (data as unknown[]).map((e: unknown) => {
          const exam = e as Record<string, unknown>
          const qArr = exam.question_count as Array<{ count: number }> | null
          return { ...exam, question_count: qArr?.[0]?.count ?? 0 }
        }) as unknown as Exam[]
        setExams(examsData)
        const uniqueYears = [...new Set(examsData.map(e => e.year))].sort((a, b) => b - a)
        setYears(uniqueYears)
      }
      setLoading(false)
    }
    load()
  }, [router, supabase])

  // Danh sách môn có đề, sắp xếp theo thứ tự ưu tiên
  const subjects = useMemo<Subject[]>(() => {
    const map = new Map<number, Subject>()
    exams.forEach(e => {
      if (e.subjects && !map.has(e.subject_id)) map.set(e.subject_id, e.subjects)
    })
    return [...map.values()].sort((a, b) => {
      const ai = SUBJECT_ORDER.indexOf(a.code)
      const bi = SUBJECT_ORDER.indexOf(b.code)
      return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi)
    })
  }, [exams])

  const filtered = useMemo(() => exams.filter(e => {
    const name = examDisplayName(e)
    const matchSearch = !search || name.toLowerCase().includes(search.toLowerCase())
    const matchYear = !yearFilter || e.year === yearFilter
    const matchSubject = !subjectFilter || e.subject_id === subjectFilter
    return matchSearch && matchYear && matchSubject
  }), [exams, search, yearFilter, subjectFilter])

  const isFiltered = !!(search || yearFilter || subjectFilter)

  return (
    <div className="flex flex-col min-h-screen">
      <Header />

      <main className="flex-1">
        <div className="max-w-7xl mx-auto px-6 sm:px-10 pt-16 sm:pt-20 pb-12">
          <ScrollReveal>
            <SectionNumber n={1} label="Thư viện" />
          </ScrollReveal>
          <ScrollReveal delay={0.08}>
            <DisplayHeading size="xl" className="mt-6 max-w-3xl">
              <em className="italic">Đề thi</em> THPT.
            </DisplayHeading>
          </ScrollReveal>
          <ScrollReveal delay={0.15}>
            <p className="mt-6 text-base text-ink-50">
              {loading ? '...' : `${exams.length} đề thi đang có trên U-PASS.`}
            </p>
          </ScrollReveal>
        </div>

        {/* Filter bar */}
        <div className="border-y border-line">
          {/* Row 1: Subject tabs */}
          {!loading && subjects.length > 1 && (
            <div className="border-b border-line">
              <div className="max-w-7xl mx-auto px-6 sm:px-10">
                <div className="flex items-center gap-1 overflow-x-auto scrollbar-none -mx-0 py-0">
                  <button
                    onClick={() => setSubjectFilter(null)}
                    className={`flex-none px-4 py-4 text-sm tracking-label border-b-2 transition-colors whitespace-nowrap ${
                      !subjectFilter
                        ? 'border-ink text-ink'
                        : 'border-transparent text-ink-30 hover:text-ink'
                    }`}
                  >
                    Tất cả
                  </button>
                  {subjects.map(s => (
                    <button
                      key={s.id}
                      onClick={() => setSubjectFilter(subjectFilter === s.id ? null : s.id)}
                      className={`flex-none px-4 py-4 text-sm tracking-label border-b-2 transition-colors whitespace-nowrap ${
                        subjectFilter === s.id
                          ? 'border-ink text-ink'
                          : 'border-transparent text-ink-30 hover:text-ink'
                      }`}
                    >
                      {s.name}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Row 2: Search + Year */}
          <div className="max-w-7xl mx-auto px-6 sm:px-10 py-5 flex flex-col sm:flex-row sm:items-center gap-4">
            <div className="relative flex-1">
              <Search size={14} className="absolute left-0 top-1/2 -translate-y-1/2 text-ink-30" />
              <input
                type="text"
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Tìm đề thi..."
                className="w-full pl-7 py-2 bg-transparent border-0 text-base text-ink placeholder:text-ink-30 focus:outline-none"
              />
            </div>
            <div className="flex items-center gap-4 flex-wrap">
              <span className="text-xs tracking-label text-ink-50">Năm</span>
              <button
                onClick={() => setYearFilter(null)}
                className={`text-sm tracking-label transition-colors ${
                  !yearFilter ? 'text-ink' : 'text-ink-30 hover:text-ink'
                }`}
              >
                Tất cả
              </button>
              {years.map(y => (
                <button
                  key={y}
                  onClick={() => setYearFilter(yearFilter === y ? null : y)}
                  className={`text-sm tracking-label transition-colors ${
                    yearFilter === y ? 'text-ink' : 'text-ink-30 hover:text-ink'
                  }`}
                >
                  {y}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Result count */}
        {isFiltered && !loading && (
          <div className="max-w-7xl mx-auto px-6 sm:px-10 pt-6 flex items-center gap-4">
            <p className="text-xs tracking-label text-ink-50">
              {filtered.length} kết quả phù hợp
            </p>
            <button
              onClick={() => { setSearch(''); setYearFilter(null); setSubjectFilter(null) }}
              className="text-xs tracking-label text-ink-30 hover:text-ink transition-colors"
            >
              Xóa bộ lọc ×
            </button>
          </div>
        )}

        {/* Exam list */}
        <div className="max-w-7xl mx-auto px-6 sm:px-10 py-10 pb-24">
          {loading ? (
            <div className="space-y-0">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="border-t border-line py-7 animate-pulse">
                  <div className="grid grid-cols-12 gap-6">
                    <div className="col-span-1 h-3 bg-line rounded w-8" />
                    <div className="col-span-7 h-6 bg-line rounded w-2/3" />
                    <div className="col-span-2 h-3 bg-line rounded w-12" />
                    <div className="col-span-2 h-3 bg-line rounded w-16" />
                  </div>
                </div>
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-24 border-t border-line">
              <p className="font-display text-3xl text-ink-50 italic">
                {subjectFilter
                  ? `Chưa có đề ${subjects.find(s => s.id === subjectFilter)?.name ?? ''}.`
                  : 'Không tìm thấy đề thi phù hợp.'}
              </p>
              <button
                onClick={() => { setSearch(''); setYearFilter(null); setSubjectFilter(null) }}
                className="mt-6 text-sm tracking-label text-ink link-editorial"
              >
                Xóa bộ lọc →
              </button>
            </div>
          ) : (
            <ul>
              {filtered.map((exam, i) => (
                <li key={exam.id}>
                  <Link
                    href={`/exams/${exam.id}`}
                    className="group block border-t border-line py-7 hover:bg-paper-soft transition-colors -mx-6 sm:-mx-10 px-6 sm:px-10"
                  >
                    <div className="grid grid-cols-12 gap-4 sm:gap-6 items-baseline">
                      <span className="col-span-2 sm:col-span-1 text-xs tracking-label text-ink-50 font-mono pt-1">
                        ({String(i + 1).padStart(2, '0')})
                      </span>
                      <div className="col-span-9 sm:col-span-6">
                        <h2 className="font-display text-2xl sm:text-3xl text-ink leading-tight group-hover:italic transition-all">
                          {examDisplayName(exam)}
                        </h2>
                        <p className="mt-2 text-xs tracking-label text-ink-50">
                          {exam.subjects?.name || 'Môn học'}
                          {exam.question_count ? ` · ${exam.question_count} câu` : ''}
                          {' · ~90 phút'}
                        </p>
                      </div>
                      <span className="hidden sm:block sm:col-span-2 text-sm text-ink-50">
                        {exam.year}
                      </span>
                      <span className="hidden sm:block sm:col-span-2 text-sm text-ink-50">
                        {exam.exam_type ? (EXAM_TYPE_LABELS[exam.exam_type] || exam.exam_type) : ''}
                      </span>
                      <span className="col-span-1 text-right text-ink-30 group-hover:text-ink transition-colors">
                        →
                      </span>
                    </div>
                  </Link>
                </li>
              ))}
              <li className="border-t border-line" />
            </ul>
          )}
        </div>
      </main>

      <Footer />
    </div>
  )
}
