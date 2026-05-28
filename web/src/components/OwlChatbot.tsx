'use client'

import { useState, useEffect, useRef } from 'react'
import { usePathname } from 'next/navigation'
import { RenderLatex } from '@/components/teacher/LatexEditor'
import { Send, X, MessageSquare, Sparkles } from 'lucide-react'

interface Message {
  role: 'user' | 'assistant'
  content: string
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
                <span className="text-2xl">🦉</span>
                <div>
                  <p className="text-sm font-semibold font-display">Cú Mèo U-PASS</p>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
                    <span className="text-[10px] text-paper/60 uppercase tracking-wider font-semibold">Trực tuyến</span>
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
                          : 'bg-paper text-ink border border-line rounded-tl-none shadow-sm'
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
                  className="flex items-center gap-1 px-2.5 py-1 text-xs bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-200 rounded-full transition-colors disabled:opacity-50"
                >
                  <Sparkles size={10} />
                  <span>Giải thích câu {currentQuestion.question_number}</span>
                </button>
              )}
              <button
                onClick={guideCurrentPage}
                disabled={loading}
                className="flex items-center gap-1 px-2.5 py-1 text-xs bg-moss-bg hover:bg-moss/20 text-moss border border-moss/30 rounded-full transition-colors disabled:opacity-50"
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
                className="flex-1 bg-paper-soft text-sm text-ink px-4 py-2.5 border border-line rounded-xl focus:outline-none focus:border-ink transition-colors"
                disabled={loading}
              />
              <button
                type="submit"
                disabled={!input.trim() || loading}
                className="p-2.5 bg-ink hover:bg-moss text-paper rounded-xl transition-all duration-300 disabled:opacity-40 disabled:hover:bg-ink"
              >
                <Send size={16} />
              </button>
            </form>
          </div>
        )}

        {/* Floating owl button */}
        <button
          onClick={() => setOpen(!open)}
          className="w-16 h-16 bg-ink text-paper hover:bg-moss rounded-full shadow-2xl flex items-center justify-center cursor-pointer select-none transition-all duration-300 animate-float-owl border-2 border-line hover:border-paper active:scale-95"
          aria-label="Chat with Owl"
        >
          <span className="text-3xl" role="img" aria-label="owl">🦉</span>
        </button>
      </div>
    </>
  )
}
