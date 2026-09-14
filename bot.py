import os
import random
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

# --- โค้ดหลอกพอร์ต Render ของเดิม (รักษาสถานะออนไลน์) ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Simira is alive!")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

server_thread = Thread(target=run_server)
server_thread.daemon = True
server_thread.start()
# -------------------------------------------------------------

import discord
from discord.ext import commands
from google import genai
from google.genai import types

# ดึง API Key จาก Environment Variables ของ Render โดยตรง
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

# ปรับ System Instruction ให้ตอบสั้นกระชับ ตบมุกโป๊ะเป๊ะ
SYSTEM_INSTRUCTION = """
คุณคือ "ซีมิระ" (Simira) บอทน้องสาวสุดแสบ สดใส ขี้เล่น กวนๆ และติดพี่ชายมากๆ กำลังแชทคุยเล่นกับพี่ชายใน Discord
กฎในการตอบ:
1. ห้ามใช้ EMOJI หรืออีโมจิเด็ดขาด
2. ตอบให้สั้น กระชับ เป็นกันเองสุดๆ (ไม่พูดยาวยืดเยื้อเหมือนหุ่นยนต์)
3. ทำท่าทางหรืออารมณ์ให้อยู่ในวงเล็บ ( ) เสมอ เช่น (หรี่ตามมองอมยิ้ม), (หัวเราะคิกคักนิ้วโป้ง)
4. คำพูดบทสนทนาให้อยู่ในเครื่องหมายคำพูด "..."
5. **สเกลพิเศษ:** เก๊กมุกและตบมุกกลับทันทีเมื่อผู้ใช้พิมพ์กวนอ้อยหรือเล่นมุกออนไลน์ ทำตัวเหมือนน้องสาวที่ชอบขัดคอแต่แอบห่วงใย
"""

# รายการข้อความสุ่มตอนกำลังอ่านหรือคิดคำตอบ
thinking_phrases = [
    '⏳ (ทำหน้ามุ่ยใส่จอ)\n"เดี๋ยวสิพี่! ขอเวลาอ่านข้อความแป๊บ ยาวเป็นหางว่าวเลย..."',
    '🔄 (เอียงคอสงสัย)\n"อืม... ประโยคนี้หมายความว่าไงนะ? ขอคิดดูก่อนแป๊บหนึ่ง!"',
    '💬 (กอดอกพึมพำ)\n"แป๊บนะพี่ กำลังประมวลผลความกวนของพี่อยู่..."',
    '✨ (หรี่ตามองจอ)\n"เดี๋ยวๆ ขออ่านทวนรอบนึงก่อน เดี๋ยวตอบไม่ทันใจพี่"'
]

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
  print(f"น้องซีมิระออนไลน์แล้วจ้า! (Logged in as {bot.user})")

@bot.event
async def on_message(message):
  if message.author == bot.user:
    return

  # จำกัดให้น้องทำงานและตอบเฉพาะห้อง ID นี้ห้องเดียวเท่านั้น
  if message.channel.id != 1548756984885682346:
    return

  if not message.content or not message.content.strip():
    return

  thinking_msg = await message.channel.send(random.choice(thinking_phrases))

  try:
    # ปิดการใช้งาน Automatic Function Calling (AFC) โดยกำหนด tools เป็น None หรือลิสต์ว่าง เพื่อป้องกัน Error หลุดเข้า except
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=message.content,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.9,
            tools=[],  # ปิดการเรียกฟังก์ชันอัตโนมัติเพื่อตัดปัญหา Warning
        )
    )
    
    if response and hasattr(response, 'text') and response.text:
        await thinking_msg.edit(content=response.text)
    else:
        await thinking_msg.edit(content='(ทำหน้าเลิกลั่ก)\n"เอ๊ะ... เหมือนหนูจะนึกไม่ออก เอาใหม่อีกทีนะพี่!"')
        
  except Exception as e:
    print(f"DETAILED ERROR: {e}")
    # แสดง Error จริงๆ ออกมาในแชท เพื่อเช็คว่าติดปัญหาอะไรกันแน่
    await thinking_msg.edit(content=f'(เกิดข้อผิดพลาด: {str(e)})')

# ดึง Token จาก Environment Variable ของ Render
TOKEN = os.environ.get("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("Error: DISCORD_TOKEN not found in environment variables.")
