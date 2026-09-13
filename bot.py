import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

# --- โค้ดหลอกพอร์ต Render (เพิ่มเข้ามาเพื่อให้ออนไลน์ฟรี 100%) ---
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

import random
import discord
from discord.ext import commands
from google import genai
from google.genai import types

# 1. API Key ของคุณ
GEMINI_API_KEY = (
    "AIzaSyAQ.Ab8RN6L1b4pL9w13beHDnPbHg1oYn9zK11vYeQaxd6VCiC-pEw"
)
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

# เก็บเซสชันการคุยแยกตามห้อง เพื่อให้จำประวัติการคุยต่อเนื่องได้ยาวๆ
chat_sessions = {}

# คลังประโยคคุุ่มตอนโควต้าหมด (จะสลับกันพูดไม่ให้ซ้ำซาก)
quota_out_messages = [
    "(นั่งกุมขมับทำหน้ามุ่ย)\n"
    "โหลยพี่... หนูคุยกับพี่เพลินจนโควต้ารายนาทีเต็มแล้วเนี่ย! ขอเวลาพักแป๊บนะพี่ เดี๋ยวค่อยมาลุยกันใหม่!",
    "(นอนแผหล่าทำท่าทางเหนื่อยหอบ)\n"
    "ไม่ไหวแล้ว สมองหนูช็อตเพราะความกวนของพี่เนี่ยแหละ! พักแป๊บนะเดี๋ยวสมองรีบูตทัน!",
    "(กอดอกพองลมทำค้อนใส่)\n"
    "โหล่พี่ เล่นยิงคำถามรัวเป็นปืนกลแบบนี้ โควต้าฟรีหนูหมดเกลี้ยงเลย! รอแป๊บให้น้องหายเหนื่อยก่อนนะ!",
    "(เอามือกอดขมับทำหน้าเอือมระอา)\n"
    "โอ๊ยพ่อคุณ สมองหนูรับไม่ทันแล้ว โควต้าหมดชั่วคราว! ขอเวลาพักหายใจแป๊บเดียวนะพี่!",
    "(ชูนิ้วโป้งหน้าตายแต่หอบแฮ่ก)\n"
    "พลังงานหมดก๊อกเพราะคุยกับพี่นี่แหละ! ให้เวลาหนูชาร์จแบตแป๊บนึง เดี๋ยวกลับมาป่วนใหม่!",
]


@bot.event
async def on_ready():
  print(f"น้องซีมิระออนไลน์แล้วจ้า! (Logged in as {bot.user})")


@bot.event
async def on_message(message):
  if message.author == bot.user:
    return

  channel_id = message.channel.id

  # ถ้าห้องนี้ยังไม่มีเซสชันการคุย ให้สร้างใหม่พร้อมใส่ System Instruction
  if channel_id not in chat_sessions:
    chat_sessions[channel_id] = client.chats.create(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.9,
        ),
    )

  chat = chat_sessions[channel_id]

  try:
    # ส่งข้อความไปคุยกับ Gemini แบบต่อเนื่อง
    response = chat.send_message(message.content)
    await message.channel.send(response.text)

  except Exception as e:
    # พริ้นต์ Error ออกมาดูที่หน้า Logs ของ Render เพื่อเช็กสาเหตุที่แท้จริง
    print(f"GEMINI ERROR DEBUG: {e}")
    
    error_str = str(e)
    if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
      selected_msg = random.choice(quota_out_messages)
      await message.channel.send(selected_msg)
    else:
      # ส่งข้อความบอก Error ดิบๆ กลับมาในแชท Discord ชั่วคราว เพื่อเราจะได้รู้ว่าติดปัญหาอะไรกันแน่
      await message.channel.send(f"(ทำหน้าเลิกลั่ก)\nพิมพ์บอกพี่: เกิดข้อผิดพลาดตัวนี้จ้า -> `{e}`")


# ดึง Token จาก Environment Variables บน Render อัตโนมัติ
TOKEN = os.environ.get("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("Error: DISCORD_TOKEN not found in environment variables.")
