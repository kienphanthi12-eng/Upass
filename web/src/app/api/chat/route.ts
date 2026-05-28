import { NextResponse } from 'next/server'

export async function POST(req: Request) {
  try {
    const { messages, context } = await req.json()
    const apiKey = process.env.ALIBABA_API_KEY || 'sk-68d1a7b992334c2180b2bd3230063c24'
    const endpoint = 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions'

    // Construct the context string to inject into the system prompt
    let contextInstructions = ""
    if (context) {
      const { pathname, currentQuestion } = context
      contextInstructions += `\nNgữ cảnh trang hiện tại của người dùng:
- Đường dẫn trang (Pathname): ${pathname || "Không rõ"}`

      if (currentQuestion) {
        contextInstructions += `\n- Câu hỏi đang xem (Câu số ${currentQuestion.question_number || '?'}) có nội dung:
"""
${currentQuestion.content}
"""`
        if (currentQuestion.options) {
          contextInstructions += `\nCác lựa chọn đáp án:
${Object.entries(currentQuestion.options).map(([k, v]) => `- [${k}]: ${v}`).join('\n')}`
        }
        if (currentQuestion.correct_answer) {
          contextInstructions += `\n- Đáp án đúng của câu hỏi này là: ${currentQuestion.correct_answer}`
        }
      }
    }

    const systemPrompt = `Bạn là trợ lý AI thông minh mang tên "Cú Mèo U-PASS", hiển thị dưới dạng một chú cú mèo nhỏ bay lượn xung quanh website luyện thi THPT U-PASS.
Nhiệm vụ của bạn là hướng dẫn người dùng sử dụng ứng dụng, giải đáp các thắc mắc về tính năng luyện thi của U-PASS, và đặc biệt là hướng dẫn giải các câu hỏi học tập (toán, lý, hóa...) khi người dùng yêu cầu.

Phong cách trả lời:
- Luôn ngắn gọn, đi thẳng vào vấn đề, chuyên nghiệp nhưng vô cùng nhiệt tình, tận tâm.
- Xưng hô thân mật là "Cú Mèo" (hoặc "mình") và gọi người dùng là "bạn" hoặc "sĩ tử".
- Khi giải bài tập, hãy trình bày các bước suy luận rõ ràng, mạch lạc, dễ hiểu nhất có thể.

Dưới đây là ngữ cảnh thời gian thực về vị trí và câu hỏi học sinh đang tương tác trên giao diện:${contextInstructions}`

    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: 'qwen-plus',
        messages: [
          { role: 'system', content: systemPrompt },
          ...messages
        ],
        temperature: 0.7
      })
    })

    const data = await response.json()
    if (data.error) {
      return NextResponse.json({ error: data.error.message }, { status: 400 })
    }

    const reply = data.choices?.[0]?.message?.content || "Cú Mèo đang suy nghĩ chút..."
    return NextResponse.json({ reply })
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }
}
