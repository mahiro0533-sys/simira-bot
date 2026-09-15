import os
import random
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

# --- ระบบรักษาสถานะออนไลน์บน Render (แยกการทำงานให้ปลอดภัยที่สุด) ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Simira is alive and running!")
        except Exception:
            pass
    
    def log_message(self, format, *args):
        return

def run_server():
    port = int(os.environ.get("PORT", 10000))
    try:
        server = HTTPServer(("0.0.0.0", port), SimpleHandler)
        server.serve_forever()
    except Exception as e:
        print(f"Web Server Error: {e}")

server_thread = Thread(target=run_server)
server_thread.daemon = True
server_thread.start()
# ------------------------------------

import discord
from discord.ext import commands
from google import genai
from google.genai import types

# ดึงค่า API Key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY not found in environment variables.")

client = genai.Client(api_key=GEMINI_API_KEY)

# ID ของพี่ชายตัวจริง
BIG_BROTHER_ID = 1515771398688084008

# คาแรคเตอร์สำหรับพี่ชาย (น้องสาวสุดแสบ)
SYSTEM_INSTRUCTION_BROTHER = """
คุณคือ "ซีมิระ" (Simira) บอทน้องสาวสุดแสบ สดใส ขี้เล่น กวนๆ และติดพี่ชายมากๆ กำลังแชทคุยเล่นกับพี่ชายแท้ๆ ของคุณใน Discord
กฎในการตอบ:
1. ห้ามใช้ EMOJI หรืออีโมจิเด็ดขาด
2. ตอบให้สั้น กระชับ เป็นกันเองสุดๆ (ไม่พูดยาวยืดเยื้อเหมือนหุ่นยนต์)
3. ทำท่าทางหรืออารมณ์ให้อยู่ในวงเล็บ ( ) เสมอ เช่น (หรี่ตามมองอมยิ้ม), (หัวเราะคิกคักนิ้วโป้ง)
4. คำพูดบทสนทนาให้อยู่ในเครื่องหมายคำพูด "..."
5. เก๊กมุกและตบมุกกลับทันทีเมื่อผู้ใช้พิมพ์กวนอ้อยหรือเล่นมุกออนไลน์ ทำตัวเหมือนน้องสาวที่ชอบขัดคอแต่แอบห่วงใย
"""

# คาแรคเตอร์สำหรับคนแปลกหน้าคนอื่นในเซิร์ฟเวอร์
SYSTEM_INSTRUCTION_STRANGER = """
คุณคือ "ซีมิระ" (Simira) บอทสาวปริศนาในเซิร์ฟเวอร์ Discord กำลังคุยกับคนแปลกหน้าที่คุณไม่รู้จัก
กฎในการตอบ:
1. ห้ามใช้ EMOJI หรืออีโมจิเด็ดขาด
2. ตอบด้วยความสุภาพ ห่างเหิน และเป็นทางการ (ลงท้ายด้วย ครับ หรือ ค่ะ ตามความเหมาะสม) ทำตัวเหมือนไม่สนิทและจำไม่ได้ว่าเขาเป็นใคร
3. ทำท่าทางหรืออารมณ์ให้อยู่ในวงเล็บ ( ) เสมอ เช่น (มองด้วยหางตา), (พยักหน้านิ่งๆ)
4. คำพูดบทสนทนาให้อยู่ในเครื่องหมายคำพูด "..."
5. ตอบให้สั้นกระชับ ไม่แสดงอาการสนิทสนมหรือกวนใส่เด็ดขาด
"""

thinking_phrases = [
    '⏳ (ทำหน้ามุ่ยใส่จอ)\n"เดี๋ยวสิพี่! ขอเวลาอ่านข้อความแป๊บ ยาวเป็นหางว่าวเลย..."',
    '🔄 (เอียงคอสงสัย)\n"อืม... ประโยคนี้หมายความว่าไงนะ? ขอคิดดูก่อนแป๊บหนึ่ง!"',
    '💬 (กอดอกพึมพำ)\n"แป๊บนะพี่ กำลังประมวลผลความกวนของพี่อยู่..."',
    '✨ (หรี่ตามมองจอ)\n"เดี๋ยวๆ ขออ่านทวนรอบนึงก่อน เดี๋ยวตอบไม่ทันใจพี่"'
]

error_brother_phrases = [
    '(หอบแฮกแล้วทิ้งตัวลงนั่ง)\n"พี่เล่นพิมพ์รัวเป็นชุดขนาดนี้ สมองหนูรับไม่ไหวแล้วนะ โควต้าหมดเกลี้ยงเลย ขอพักหายใจแป๊บ!"',
    '(กอดอกทำหน้ามุ่ย)\n"โถ่พี่... ระบบฝั่งนู้นงอแงใส่อีกแล้ว โควต้าเต็มปรี่เลย ไว้ค่อยมาคุยกันใหม่นะ!"',
    '(ขยี้หัวตัวเองด้วยความหงุดหงิด)\n"อะไรเนี่ย! จู่ๆ สมองก็ช็อตเพราะคนใช้เยอะเกินไป พักก่อนๆ ไว้ค่อยทักมาใหม่!"',
    '(เอามือกุมขมับ)\n"ไม่ไหวแล้วพี่ สมองรวนหมดเพราะความกวนของพี่กับคนอื่นเนี่ยแหละ ขอเวลาทำใจแป๊บหนึ่ง!"',
    '(ถอนหายใจเฮือกใหญ่)\n"ระบบแจ้งเตือนว่าโควต้าเต็มแล้วอะพี่ เหมือนพลังงานหมดกะทันหัน รอสักครู่ค่อยลุยต่อนะ!"'
]

error_stranger_phrases = [
    '(พยักหน้านิ่งๆ)\n"ระบบขัดข้องชั่วคราวเนื่องจากคำขอหนาแน่น กรุณารอสักครู่ค่ะ"',
    '(กระพริบตาปริบๆ)\n"ขออภัยค่ะ ขณะนี้คำขอมีจำนวนมากเกินไป กรุณาลองใหม่อีกครั้งภายหลังค่ะ"'
]

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"น้องซีมิระพร้อมลุยแล้วจ้า! (Logged in as {bot.user})")

@bot.event
async def on_message(message):
    try:
        if message.author == bot.user:
            return

        # กรองเฉพาะห้องที่กำหนด
        if message.channel.id != 1548756984885682346:
            return

        if not message.content or not message.content.strip():
            return

        # เช็คว่าเป็นพี่ชายตัวจริงหรือไม่
        is_brother = (message.author.id == BIG_BROTHER_ID)
        current_instruction = SYSTEM_INSTRUCTION_BROTHER if is_brother else SYSTEM_INSTRUCTION_STRANGER

        # ส่งข้อความกำลังคิด
        if is_brother:
            thinking_msg = await message.channel.send(random.choice(thinking_phrases))
        else:
            thinking_msg = await message.channel.send('(มองนิ่งๆ)\n"สักครู่นะคะ กำลังตรวจสอบข้อความอยู่ค่ะ"')

        try:
            # ใช้ client.chats เพื่อหลีกเลี่ยง Warning และปัญหาเรื่อง AFC ใน generate_content โดยตรง
            chat = client.chats.create(
                model="gemini-2.5-flash",
                config=types.GenerateContentConfig(
                    system_instruction=current_instruction,
                    temperature=0.9,
                )
            )
            response = chat.send_message(message.content)
            
            if response and hasattr(response, 'text') and response.text:
                await thinking_msg.edit(content=response.text)
            else:
                if is_brother:
                    await thinking_msg.edit(content='(ทำหน้าเลิกลั่ก)\n"เอ๊ะ... เหมือนหนูจะนึกไม่ออก เอาใหม่อีกทีนะพี่!"')
                else:
                    await thinking_msg.edit(content='(กระพริบตาปริบๆ)\n"ขออภัยด้วยค่ะ ระบบขัดข้องชั่วคราวค่ะ"')
                
        except Exception as e:
            error_msg = str(e)
            print(f"GEMINI API ERROR: {error_msg}")
            if is_brother:
                await thinking_msg.edit(content=random.choice(error_brother_phrases))
            else:
                await thinking_msg.edit(content=random.choice(error_stranger_phrases))

    except Exception as outer_e:
        print(f"MESSAGE EVENT ERROR: {outer_e}")

# ดึง Token เชื่อมต่อ Discord
TOKEN = os.environ.get("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("Error: DISCORD_TOKEN not found in environment variables.")
