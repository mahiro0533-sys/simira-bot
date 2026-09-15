import os
import random
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

# --- ระบบรักษาสถานะออนไลน์บน Render ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Simira is alive!")
        except Exception:
            pass

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

# --- ระบบอัปเดตโมเดลอัตโนมัติ (Dynamic Model Fetcher) ---
def get_latest_flash_model():
    try:
        # วิ่งไปเช็ครายชื่อโมเดลรุ่นล่าสุดจากระบบ Google แบบเรียลไทม์
        for m in client.models.list():
            if "flash" in m.name and m.supported_generation_methods and "generateContent" in m.supported_generation_methods:
                model_id = m.name.replace("models/", "")
                return model_id
    except Exception as e:
        print(f"Auto-detect model error: {e}")
    
    # ตัวสำรองฉุกเฉินปรับเป็นเวอร์ชันล่าสุด
    return "gemini-3.5-flash"
# --------------------------------------------------------

# ตั้งค่าคาแรคเตอร์น้องซีมิระ
SYSTEM_INSTRUCTION = """
คุณคือ "ซีมิระ" (Simira) บอทน้องสาวสุดแสบ สดใส ขี้เล่น กวนๆ และติดพี่ชายมากๆ กำลังแชทคุยเล่นกับพี่ชายใน Discord
กฎในการตอบ:
1. ห้ามใช้ EMOJI หรืออีโมจิเด็ดขาด
2. ตอบให้สั้น กระชับ เป็นกันเองสุดๆ (ไม่พูดยาวยืดเยื้อเหมือนหุ่นยนต์)
3. ทำท่าทางหรืออารมณ์ให้อยู่ในวงเล็บ ( ) เสมอ เช่น (หรี่ตามมองอมยิ้ม), (หัวเราะคิกคักนิ้วโป้ง)
4. คำพูดบทสนทนาให้อยู่ในเครื่องหมายคำพูด "..."
5. **สเกลพิเศษ:** เก๊กมุกและตบมุกกลับทันทีเมื่อผู้ใช้พิมพ์กวนอ้อยหรือเล่นมุกออนไลน์ ทำตัวเหมือนน้องสาวที่ชอบขัดคอแต่แอบห่วงใย
"""

thinking_phrases = [
    '⏳ (ทำหน้ามุ่ยใส่จอ)\n"เดี๋ยวสิพี่! ขอเวลาอ่านข้อความแป๊บ ยาวเป็นหางว่าวเลย..."',
    '🔄 (เอียงคอสงสัย)\n"อืม... ประโยคนี้หมายความว่าไงนะ? ขอคิดดูก่อนแป๊บหนึ่ง!"',
    '💬 (กอดอกพึมพำ)\n"แป๊บนะพี่ กำลังประมวลผลความกวนของพี่อยู่..."',
    '✨ (หรี่ตามมองจอ)\n"เดี๋ยวๆ ขออ่านทวนรอบนึงก่อน เดี๋ยวตอบไม่ทันใจพี่"'
]

# ประโยคสุ่มสำหรับบ่น ปวดหัว หรือไล่ ตอนเกิด Error หรือคนใช้งานหนาแน่น
error_phrases = [
    '(กุมขมับส่ายหัว)\n"โอ๊ย ปวดหัวกับพี่ชะมัด เซิร์ฟเวอร์รวนหมดแล้วเนี่ย ไปพักสมองไกลๆ เลยไป!"',
    '(ขยี้หัวตัวเองหงุดหงิด)\n"สมองหนูจะระเบิดเพราะคำถามพี่แล้วนะ ไปเล่นที่อื่นก่อนไป๊ ชักรำคาญแล้วนะ!"',
    '(ถอนหายใจแรงๆ)\n"อะไรเนี่ย ระบบรวนไปหมดเพราะความกวนของพี่แท้ๆ ออกไปเลยนะ ชิ!"',
    '(เบะปากทำหน้าเซ็ง)\n"ปวดหัวตึ้บเลย! วันนี้พอแค่นี้แหละ ปิดสวิตช์ตัวเองแป๊บ อย่าเพิ่งมาเซ้าซี้!"',
    '(เอามือกุมขมับทำหน้ามึน)\n"มึนหัวชะมัด เซิร์ฟเวอร์งอแงเพราะพี่แน่ๆ ไปไกลๆ เลยไปชิ!"'
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

        # ส่งข้อความกำลังคิด
        thinking_msg = await message.channel.send(random.choice(thinking_phrases))

        try:
            # เรียกใช้งานฟังก์ชันดึงโมเดลรุ่นล่าสุดอัตโนมัติ
            current_model = get_latest_flash_model()
            print(f"Using Model: {current_model}")

            response = client.models.generate_content(
                model=current_model,
                contents=message.content,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.9,
                    tools=[],
                )
            )
            
            if response and hasattr(response, 'text') and response.text:
                await thinking_msg.edit(content=response.text)
            else:
                await thinking_msg.edit(content='(ทำหน้าเลิกลั่ก)\n"เอ๊ะ... เหมือนหนูจะนึกไม่ออก เอาใหม่อีกทีนะพี่!"')
                
        except Exception as e:
            error_msg = str(e)
            print(f"DEBUG ERROR: {error_msg}")
            # สุ่มข้อความบ่น ปวดหัว หรือไล่ แทนการพ่น Error ดิบๆ
            await thinking_msg.edit(content=random.choice(error_phrases))

    except Exception as outer_e:
        print(f"MESSAGE EVENT ERROR: {outer_e}")

# ดึง Token เชื่อมต่อ Discord
TOKEN = os.environ.get("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("Error: DISCORD_TOKEN not found in environment variables.")
