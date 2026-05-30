'use client'

import { useState, useEffect, useRef } from 'react'
import { usePathname } from 'next/navigation'
import { RenderLatex } from '@/components/teacher/LatexEditor'
import { Send, X, MessageSquare, Sparkles } from 'lucide-react'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

// U-PASS Official Academic Owl Mascot (Line-art SVG)
export function OwlMascotIcon({ size = 32, className = '' }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`text-current ${className}`}
    >
      {/* Ear tufts */}
      <path
        d="M 28 22 L 17 11 L 32 19"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M 72 22 L 83 11 L 68 19"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* Body */}
      <path
        d="M 50 15 C 31 15 24 28 24 50 C 24 72 31 84 50 84 C 69 84 76 72 76 50 C 76 28 69 15 50 15 Z"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
      />
      {/* Big Glasses circles */}
      <circle cx="38" cy="40" r="10.5" stroke="currentColor" strokeWidth="2.2" />
      <circle cx="62" cy="40" r="10.5" stroke="currentColor" strokeWidth="2.2" />
      {/* Glasses bridge */}
      <path d="M 48.5 40 L 51.5 40" stroke="currentColor" strokeWidth="2.2" />
      {/* Eyes Pupils */}
      <circle cx="38" cy="40" r="2.5" fill="currentColor" />
      <circle cx="62" cy="40" r="2.5" fill="currentColor" />
      {/* Beak */}
      <path d="M 50 48 L 47.5 53 L 52.5 53 Z" fill="currentColor" />
      {/* Cheeks lines */}
      <path d="M 28 50 C 31 52 33 52 36 50" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M 72 50 C 69 52 67 52 64 50" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      {/* Feather chest details */}
      <path d="M 46 59 Q 50 62 54 59" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M 42 66 Q 50 70 58 66" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      {/* Feet / Claws */}
      <path d="M 40 84 L 38 89" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
      <path d="M 43 84 L 43 89" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
      <path d="M 46 84 L 48 89" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
      <path d="M 54 84 L 52 89" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
      <path d="M 57 84 L 57 89" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
      <path d="M 60 84 L 62 89" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
      {/* Graduation cap */}
      <path d="M 33 16 L 50 11 L 67 16 L 50 21 Z" fill="#e8ecdf" stroke="#4a5d3a" strokeWidth="1.75" strokeLinejoin="round" />
      <path d="M 50 21 L 50 25" stroke="#4a5d3a" strokeWidth="1.75" />
      <path d="M 60 17.5 L 63 23 L 61 24" fill="none" stroke="#4a5d3a" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export default function OwlChatbot() {
  const pathname = usePathname()
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: 'Chào sĩ tử! 🦉 Mình là Cú Mèo U-PASS. Mình có thể giúp bạn giải thích câu hỏi đang làm, hoặc hướng dẫn bạn sử dụng các tính năng trên website. Bạn cần mình hỗ trợ gì không?'
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [currentQuestion, setCurrentQuestion] = useState<any>(null)
  
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Listen to window.__current_question__ changes
  useEffect(() => {
    const interval = setInterval(() => {
      if (typeof window !== 'undefined') {
        const q = (window as any).__current_question__
        if (q !== currentQuestion) {
          setCurrentQuestion(q)
        }
      }
    }, 1000)
    return () => clearInterval(interval)
  }, [currentQuestion])

  // Scroll to bottom on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, open])

  const handleSend = async (textToSend?: string) => {
    const text = (textToSend || input).trim()
    if (!text || loading) return

    if (!textToSend) setInput('')

    const newMessages = [...messages, { role: 'user', content: text } as Message]
    setMessages(newMessages)
    setLoading(true)

    try {
      // Build context payload
      const context = {
        pathname,
        currentQuestion: currentQuestion || null
      }

      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: newMessages.map(m => ({ role: m.role, content: m.content })),
          context
        })
      })

      const data = await res.json()
      if (data.error) {
        setMessages(prev => [
          ...prev,
          { role: 'assistant', content: `Cú Mèo gặp sự cố rồi: ${data.error}` }
        ])
      } else {
        setMessages(prev => [
          ...prev,
          { role: 'assistant', content: data.reply }
        ])
      }
    } catch (err: any) {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: 'Không thể kết nối với Cú Mèo. Bạn kiểm tra lại kết nối mạng nhé.' }
      ])
    } finally {
      setLoading(false)
    }
  }

  const explainCurrentQuestion = () => {
    if (!currentQuestion) return
    handleSend(`Giải thích giúp mình câu hỏi hiện tại (Câu ${currentQuestion.question_number})`)
  }

  const guideCurrentPage = () => {
    handleSend(`Hướng dẫn mình các tính năng trên trang này với`)
  }

  return (
    <>
      {/* Floating Style Injector */}
      <style jsx global>{`
        @keyframes floatOwl {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          50% { transform: translateY(-8px) rotate(1deg); }
        }
        .animate-float-owl {
          animation: floatOwl 4s ease-in-out infinite;
        }
      `}</style>

      {/* Floating owl widget */}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end select-none">
        
        {/* Chat window */}
        {open && (
          <div className="mb-4 w-[340px] sm:w-[380px] h-[480px] bg-paper border border-line shadow-2xl rounded-2xl flex flex-col overflow-hidden animate-in fade-in slide-in-from-bottom duration-200">
            {/* Header */}
            <div className="px-4 py-3.5 bg-ink text-paper flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="bg-snow/10 p-1 rounded-lg">
                  <OwlMascotIcon size={26} className="text-paper" />
                </div>
                <div>
                  <p className="text-sm font-semibold font-display italic tracking-wide">Cú Mèo U-PASS</p>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
                    <span className="text-[9px] text-paper/60 uppercase tracking-wider font-semibold font-mono">Trực tuyến</span>
                  </div>
                </div>
              </div>
              <button 
                onClick={() => setOpen(false)}
                className="p-1 hover:bg-paper/10 rounded transition-colors text-paper/70 hover:text-paper"
              >
                <X size={18} />
              </button>
            </div>

            {/* Chat Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-paper-soft/40">
              {messages.map((m, idx) => {
                const isUser = m.role === 'user'
                return (
                  <div key={idx} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
                    <div 
                      className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                        isUser 
                          ? 'bg-ink text-paper rounded-tr-none' 
                          : 'bg-paper text-ink border border-line rounded-tl-none shadow-sm font-sans'
                      }`}
                    >
                      {isUser ? (
                        <p className="white-space-pre-wrap">{m.content}</p>
                      ) : (
                        <RenderLatex text={m.content} />
                      )}
                    </div>
                  </div>
                )
              })}
              {loading && (
                <div className="flex justify-start">
                  <div className="bg-paper text-ink border border-line rounded-2xl rounded-tl-none px-4 py-3 shadow-sm flex items-center gap-1">
                    <span className="w-1.5 h-1.5 bg-ink/40 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-1.5 h-1.5 bg-ink/40 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-1.5 h-1.5 bg-ink/40 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Context chips */}
            <div className="px-3 py-2 bg-paper border-t border-line flex flex-wrap gap-1.5">
              {currentQuestion && (
                <button
                  onClick={explainCurrentQuestion}
                  disabled={loading}
                  className="flex items-center gap-1 px-2.5 py-1 text-xs bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-200 rounded-full transition-colors disabled:opacity-50 font-sans"
                >
                  <Sparkles size={10} />
                  <span>Giải thích câu {currentQuestion.question_number}</span>
                </button>
              )}
              <button
                onClick={guideCurrentPage}
                disabled={loading}
                className="flex items-center gap-1 px-2.5 py-1 text-xs bg-moss-bg hover:bg-moss/20 text-moss border border-moss/30 rounded-full transition-colors disabled:opacity-50 font-sans"
              >
                <MessageSquare size={10} />
                <span>Hướng dẫn trang này</span>
              </button>
            </div>

            {/* Input area */}
            <form 
              onSubmit={e => { e.preventDefault(); handleSend() }}
              className="p-3 border-t border-line bg-paper flex items-center gap-2"
            >
              <input
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                placeholder="Hỏi Cú Mèo điều gì đó..."
                className="flex-1 bg-paper-soft text-sm text-ink px-4 py-2.5 border border-line rounded-xl focus:outline-none focus:border-ink transition-colors font-sans"
                disabled={loading}
              />
              <button
                type="submit"
                disabled={!input.trim() || loading}
                className="p-2.5 bg-ink hover:bg-moss text-paper rounded-xl transition-all duration-300 disabled:opacity-40 disabled:hover:bg-ink cursor-pointer"
              >
                <Send size={16} />
              </button>
            </form>
          </div>
        )}

        {/* Floating owl button */}
        <button
          onClick={() => setOpen(!open)}
          className="w-16 h-16 bg-ink text-paper hover:bg-moss rounded-full shadow-2xl flex items-center justify-center cursor-pointer select-none transition-all duration-300 animate-float-owl border-2 border-line hover:border-paper active:scale-95 group"
          aria-label="Chat with Owl"
        >
          <OwlMascotIcon size={38} className="text-paper group-hover:scale-110 transition-transform duration-300" />
        </button>
      </div>
    </>
  )
}
