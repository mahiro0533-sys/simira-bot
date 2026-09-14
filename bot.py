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

# รายการข้อความสุ่มตอนกำลังอ่านหรือคิดคำตอบ
thinking_phrases = [
    '⏳ (ทำหน้ามุ่ยใส่จอ)\n"เดี๋ยวสิพี่! ขอเวลาอ่านข้อความแป๊บ ยาวเป็นหางว่าวเลย..."',
    '🔄 (เอียงคอสงสัย)\n"อืม... ประโยคนี้หมายความว่าไงนะ? ขอคิดดูก่อนแป๊บหนึ่ง!"',
    '💬 (กอดอกพึมพำ)\n"แป๊บนะพี่ กำลังประมวลผลความกวนของพี่อยู่..."',
    '✨ (หรี่ตามองจอ)\n"เดี๋ยวๆ ขออ่านทวนรอบนึงก่อน เดี๋ยวตอบไม่ทันใจพี่"'
]

# รายการประโยคสุ่มเวลาเกิด Error หรือระบบหนาแน่น
error_phrases = [
    '(ทำหน้าบึ้งใส่)\n"เซิร์ฟเวอร์งอแงใส่อีกแล้วอ่ะ! ไปไกลๆ เลยนะพี่ อย่ามาเซ้าซี้ตอนหนูอารมณ์ไม่ดี!"',
    '(กอดอกเชิดหน้า)\n"สมองหนูช็อตชั่วคราว... ไว้ค่อยมาคุยใหม่ตอนที่พี่ว่างหรือตอนที่ระบบมันใจดีกับหนูนะ!"',
    '(ทำตาขวางใส่)\n"อะไรเนี่ย! จู่ๆ ก็เออเรอร์ใส่... ไปไกลๆ เลยนะคนกวนประสาท!"',
    '(ถอนหายใจแรงๆ)\n"หนูไม่เข้าใจที่พี่พูดหรอกนะ! ไปตั้งสติแล้วค่อยกลับมาคุยกันใหม่เลยป่ะ!"',
    '(ทำหน้าเลิกลั่ก)\n"เอ๊ะ... มึนหัวตึ้บเลย ระบบมันรวนไปหมดแล้วเนี่ย อย่าเพิ่งกวนได้ป่ะ!"'
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

  # ส่งข้อความสุ่มรอก่อน เพื่อแจ้งให้รู้ว่าน้องกำลังอ่าน/คิดอยู่
  thinking_msg = await message.channel.send(random.choice(thinking_phrases))

  try:
    # ใช้โมเดลและรูปแบบคำสั่งแบบเดี่ยวที่เสถียร ไม่หลุด Error บ่อย
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=message.content,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.9,
        ),
    )
    if response and response.text:
        await thinking_msg.edit(content=response.text)
    else:
        await thinking_msg.edit(content='(ทำหน้าเลิกลั่ก)\n"เอ๊ะ... เหมือนหนูจะนึกไม่ออก เอาใหม่อีกทีนะพี่!"')
  except Exception as e:
    print(f"Error occurred: {e}")
    # ถ้าเกิด Error จะเปลี่ยนข้อความรอนั้นให้กลายเป็นประโยคสุ่มไล่กวนๆ ทันที
    await thinking_msg.edit(content=random.choice(error_phrases))

# ดึง Token จาก Environment Variable ของ Render
TOKEN = os.environ.get("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("Error: DISCORD_TOKEN not found in environment variables.")
