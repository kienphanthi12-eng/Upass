import asyncio
import sys
import io
from openai import AsyncOpenAI

# Fix console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

async def test_qwen():
    api_key = "sk-68d1a7b992334c2180b2bd3230063c24"
    base_url = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url
    )
    
    print("Testing qwen-plus on international endpoint...")
    try:
        resp = await client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Xin chào, hãy giới thiệu ngắn về bản thân bằng tiếng Việt."}
            ],
            max_tokens=100
        )
        print("Success! qwen-plus response:")
        print(resp.choices[0].message.content)
    except Exception as e:
        print(f"Failed for qwen-plus: {e}")

if __name__ == "__main__":
    asyncio.run(test_qwen())
