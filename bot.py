import os
import random
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from collections import defaultdict

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

# --- กำหนดไอดีเจ้าของ (พี่ชายตัวจริง) ---
OWNER_DISCORD_ID = 1515771398688084008

# --- ระบบอัปเดตโมเดลอัตโนมัติและสแกนหาตัวสำรองอัจฉริยะ ---
def get_latest_flash_model():
    available_models = []
    try:
        for m in client.models.list():
            # กรองเฉพาะรุ่นที่มีคำว่า flash และรองรับการสร้างข้อความ
            if "flash" in m.name and m.supported_generation_methods and "generateContent" in m.supported_generation_methods:
                clean_name = m.name.replace("models/", "")
                available_models.append(clean_name)
        
        if available_models:
            # เลือกตัวแรกที่ระบบสแกนเจอว่าเป็นรุ่นล่าสุด
            latest_model = available_models[0]
            print(f"Auto-detected active flash model: {latest_model}")
            return latest_model
            
    except Exception as e:
        print(f"Auto-detect model error: {e}")
    
    # ถ้าเกิดกรณีฉุกเฉินดึงรายชื่อไม่ผ่าน ระบบจะพยายามเลือกใช้ตระกูล Flash ยุคใหม่ล่าสุดทันที
    fallback_model = "gemini-3.6-flash"
    print(f"Using dynamic fallback model: {fallback_model}")
    return fallback_model
# --------------------------------------------------------

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

# --- จัดการเซสชันแชทแยกตามรายบุคคล (ใช้ระบบ Chat ของ Google GenAI โดยตรง) ---
user_chats = {}

def get_or_create_chat(user_id, model_name):
    # หากผู้ใช้เปลี่ยนโมเดล หรือยังไม่มีเซสชัน ให้สร้างใหม่
    if user_id not in user_chats:
        # กำหนดบริบทเริ่มต้นตามตัวตนของผู้ใช้
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
        
        chat = client.chats.create(
            model=model_name,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.9,
            ),
            history=initial_history
        )
        user_chats[user_id] = chat
    return user_chats[user_id]
# -----------------------------------------------------------------

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

        if message.channel.id != 1548756984885682346:
            return

        if not message.content or not message.content.strip():
            return

        thinking_msg = await message.channel.send(random.choice(thinking_phrases))

        current_model = get_latest_flash_model()
        print(f"Using Model: {current_model}")

        user_id = message.author.id
        chat_session = get_or_create_chat(user_id, current_model)

        # --- ส่วนที่เพิ่มเข้ามา: ห่อหุ้มข้อความเพื่อบอกโมเดลแบบเรียลタイムว่าใครกำลังคุยอยู่ ---
        if user_id == OWNER_DISCORD_ID:
            prompt_to_send = message.content
        else:
            prompt_to_send = f"[ผู้ใช้คนนี้ไม่ใช่พี่ชายของคุณ ห้ามเรียกว่าพี่เด็ดขาด]: {message.content}"
        # --------------------------------------------------------------------------

        response = None
        max_retries = 2
        for attempt in range(max_retries):
            try:
                # ส่งข้อความผ่านระบบ Chat Session โดยตรง (ใช้ prompt_to_send ที่คอยย้ำสถานะ)
                response = chat_session.send_message(prompt_to_send)
                if response and hasattr(response, 'text') and response.text:
                    break
            except Exception as retry_err:
                print(f"Attempt {attempt + 1} failed: {retry_err}")
                if attempt < max_retries - 1:
                    time.sleep(1.5)
                else:
                    raise retry_err

        if response and hasattr(response, 'text') and response.text:
            reply_text = response.text.strip()

            if len(reply_text) <= 2000:
                await thinking_msg.edit(content=reply_text)
            else:
                chunks = [reply_text[i:i+2000] for i in range(0, len(reply_text), 2000)]
                await thinking_msg.edit(content=chunks[0])
                for chunk in chunks[1:]:
                    await message.channel.send(chunk)
        else:
            print("WARNING: Response text was empty or invalid.")
            await thinking_msg.edit(content='(ทำหน้าเลิกลั่ก)\n"เอ๊ะ... เหมือนหนูจะนึกไม่ออก เอาใหม่อีกทีนะพี่!"')

    except Exception as outer_e:
        # พิมพ์ Error ดิบลงใน Logs ของ Render เพื่อให้คุณตรวจสอบได้ทันทีถ้ายังมีปัญหา
        print(f"MESSAGE EVENT ERROR DETECTED: {str(outer_e)}")
        import traceback
        traceback.print_exc()
        try:
            await message.channel.send(random.choice(error_phrases))
        except:
            pass

TOKEN = os.environ.get("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("Error: DISCORD_TOKEN not found in environment variables.")
