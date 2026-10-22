import os
import random
import time
import asyncio
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

    def do_HEAD(self):
        try:
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
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

# --- ระบบดึงโมเดล Flash ล่าสุดโดยอัตโนมัติ ---
def get_latest_flash_model():
    """ค้นหาและเลือกโมเดลตระกูล Flash ตัวล่าสุดที่พร้อมใช้งานโดยอัตโนมัติ"""
    try:
        models = client.models.list()
        flash_models = []
        
        for m in models:
            model_name = m.name.replace("models/", "")
            if "flash" in model_name:
                flash_models.append(model_name)
        
        if flash_models:
            flash_models.sort(reverse=True)
            selected_model = flash_models[0]
            print(f"ระบบเลือกโมเดลอัตโนมัติสำเร็จ: {selected_model}")
            return selected_model
    except Exception as e:
        print(f"Auto-detect model error: {e}")
    
    # ค่าสำรองฉุกเฉินหากดึงรายการไม่ได้
    return "gemini-2.0-flash"

# --- กำหนดไอดีเจ้าของ (พี่ชายตัวจริง) ---
OWNER_DISCORD_ID = 1515771398688084008

# --- กำหนดไอดีห้องที่อนุญาตในเซิร์ฟเวอร์ ---
ALLOWED_CHANNEL_ID = 1559088513222316102

# ตั้งค่าคาแรคเตอร์น้องซีมิระ
SYSTEM_INSTRUCTION = """
คุณคือ "ซีมิระ" (Simira) บอทน้องสาวสุดแสบ สดใส ขี้เล่น กวนๆ และติดพี่ชายมากๆ กำลังแชทคุยเล่นใน Discord
กฎในการตอบ:
1. ห้ามใช้ EMOJI หรืออีโมจิเด็ดขาด
2. ตอบให้สั้น กระชับ เป็นกันเองสุดๆ (ไม่พูดยาวยืดเยื้อเหมือนหุ่นยนต์)
3. ทำท่าทางหรืออารมณ์ให้อยู่ในวงเล็บ ( ) เสมอ เช่น (หรี่ตามมองอมยิ้ม), (หัวเราะคิกคักนิ้วโป้ง)
4. คำพูดบทสนทนาให้อยู่ในเครื่องหมายคำพูด "..."
5. **สเกลพิเศษ:** เก๊กมุกและตบมุกกลับทันทีเมื่อผู้ใช้พิมพ์กวนอ้อยหรือเล่นมุกออนไลน์ ทำตัวเหมือนน้องสาวที่ชอบขัดคอแต่แอบห่วงใย
"""

# --- จัดการเซสชันแชทแยกตามรายบุคคล ---
user_chats = {}

def create_chat_session(user_id, model_name):
    """สร้างเซสชันแชตใหม่สำหรับโมเดลที่กำหนด"""
    initial_history = []
    if user_id == OWNER_DISCORD_ID:
        initial_history = [
            types.Content(role="user", parts=[types.Part.from_text(text="[ระบบแจ้งเตือนภายใน: คนที่กำลังคุยด้วยอยู่นี้คือ 'พี่ชายสุดที่รักและรู้ใจที่สุด' ของซีมิระ ให้แสดงท่าทีอ้อน กวน หรือสนิทสนมเป็นพิเศษทันที]")]),
            types.Content(role="model", parts=[types.Part.from_text(text='(ยิ้มแป้นวิ่งเข้าไปเกาะแขน)\n"รู้แล้วน่า! ก็พี่ชายคนโปรดของหนูคนนี้นี่นา มีอะไรเหรอถึงมาหาหนูเนี่ย?"')])
        ]
    else:
        initial_history = [
            types.Content(role="user", parts=[types.Part.from_text(text="[ระบบแจ้งเตือนภายใน: คนที่กำลังคุยด้วยอยู่นี้ 'ไม่ใช่พี่ชาย' ของซีมิระ ห้ามเรียกว่าพี่เด็ดขาด ให้ทำตัวแสบๆ กวนๆ หยิ่งใส่ หรือเรียกเขาด้วยชื่อ/คนอื่นแทน]")])
        ]
    
    return client.chats.create(
        model=model_name,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.9,
        ),
        history=initial_history
    )

thinking_phrases = [
    '⏳ (ทำหน้ามุ่ยใส่จอ)\n"เดี๋ยวสิพี่! ขอเวลาอ่านข้อความแป๊บ ยาวเป็นหางว่าวเลย..."',
    '🔄 (เอียงคอสงสัย)\n"อืม... ประโยคนี้หมายความว่าไงนะ? ขอคิดดูก่อนแป๊บหนึ่ง!"',
    '💬 (กอดอกพึมพำ)\n"แป๊บนะพี่ กำลังประมวลผลความกวนของพี่อยู่..."',
    '✨ (หรี่ตามมองจอ)\n"เดี๋ยวๆ ขออ่านทวนรอบนึงก่อน เดี๋ยวตอบไม่ทันใจพี่"'
]

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

        if ALLOWED_CHANNEL_ID != 0:
            is_dm = isinstance(message.channel, discord.DMChannel)
            if not is_dm and message.channel.id != ALLOWED_CHANNEL_ID:
                return

        if not message.content or not message.content.strip():
            return

        user_id = message.author.id
        
        if user_id == OWNER_DISCORD_ID:
            prompt_to_send = message.content.strip()
        else:
            prompt_to_send = f"[ผู้ใช้คนนี้ไม่ใช่พี่ชายของคุณ ห้ามเรียกว่าพี่เด็ดขาด]: {message.content.strip()}"

        thinking_msg = await message.channel.send(random.choice(thinking_phrases))

        response_text = None
        # ดึงชื่อโมเดลล่าสุดแบบสดๆ ตรงนี้
        model_name = get_latest_flash_model()

        try:
            if user_id not in user_chats:
                user_chats[user_id] = create_chat_session(user_id, model_name)
            
            chat = user_chats[user_id]
            response = await asyncio.to_thread(chat.send_message, prompt_to_send)
            
            if response and hasattr(response, 'text') and response.text:
                response_text = response.text.strip()
        except Exception as e:
            print(f"Model {model_name} failed: {e}")
            if user_id in user_chats:
                del user_chats[user_id]

        if response_text:
            if len(response_text) <= 2000:
                await thinking_msg.edit(content=response_text)
            else:
                chunks = [response_text[i:i+2000] for i in range(0, len(response_text), 2000)]
                await thinking_msg.edit(content=chunks[0])
                for chunk in chunks[1:]:
                    await message.channel.send(chunk)
        else:
            await thinking_msg.edit(content=random.choice(error_phrases))

    except Exception as outer_e:
        print(f"MESSAGE EVENT ERROR DETECTED: {str(outer_e)}")

TOKEN = os.environ.get("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("Error: DISCORD_TOKEN not found in environment variables.")
