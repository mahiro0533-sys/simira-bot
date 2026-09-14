import os
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

# ปรับ System Instruction ให้ตอบสั้นกระชับ ตบมุกโป๊ะเป๊ะ และขำรสสนทนาต่อเนื่อง
SYSTEM_INSTRUCTION = """
คุณคือ "ซีมิระ" (Simira) บอทน้องสาวสุดแสบ สดใส ขี้เล่น กวนๆ และติดพี่ชายมากๆ กำลังแชทคุยเล่นกับพี่ชายใน Discord
กฎในการตอบ:
1. ห้ามใช้ EMOJI หรืออีโมจิเด็ดขาด
2. ตอบให้สั้น กระชับ เป็นกันเองสุดๆ (ไม่พูดยาวยืดเยื้อเหมือนหุ่นยนต์)
3. ทำท่าทางหรืออารมณ์ให้อยู่ในวงเล็บ ( ) เสมอ เช่น (หรี่ตามมองอมยิ้ม), (หัวเราะคิกคักนิ้วโป้ง)
4. คำพูดบทสนทนาให้อยู่ในเครื่องหมายคำพูด "..."
5. **สเกลพิเศษ:** เก๊กมุกและตบมุกกลับทันทีเมื่อผู้ใช้พิมพ์กวนอ้อยหรือเล่นมุกออนไลน์ ทำตัวเหมือนน้องสาวที่ชอบขัดคอแต่แอบห่วงใย
"""

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# เก็บเซสชันการคุยแยกตามห้อง
chat_sessions = {}

@bot.event
async def on_ready():
  print(f"น้องซีมิระออนไลน์แล้วจ้า! (Logged in as {bot.user})")

@bot.event
async def on_message(message):
  if message.author == bot.user:
    return

  channel_id = message.channel.id

  # ถ้าห้องนี้ยังไม่มีเซสชันการคุย ให้สร้างใหม่ด้วยรุ่น gemini-3.6-flash ที่อัปเดตแล้ว
  if channel_id not in chat_sessions:
    chat_sessions[channel_id] = client.chats.create(
        model="gemini-3.6-flash",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.9,
        ),
    )

  chat = chat_sessions[channel_id]

  try:
    # ส่งข้อความไปคุยกับ Gemini
    response = chat.send_message(message.content)
    if response and response.text:
        await message.channel.send(response.text)
    else:
        await message.channel.send('(ทำหน้าเลิกลั่ก)\n"เอ๊ะ... เหมือนหนูจะนึกไม่ออก เอาใหม่อีกทีนะพี่!"')
  except Exception as e:
    print(f"Error occurred: {e}")
    await message.channel.send(f'(ทำหน้าเลิกลั่ก)\n"พังตรงนี้เว้ยพี่: {str(e)}"')

# ดึง Token จาก Environment Variable ของ Render
TOKEN = os.environ.get("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("Error: DISCORD_TOKEN not found in environment variables.")
