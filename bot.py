import os
import random
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from collections import defaultdict, deque

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

# --- ระบบอัปเดตโมเดลอัตโนมัติ (Dynamic Model Fetcher) ---
def get_latest_flash_model():
    try:
        for m in client.models.list():
            if "flash" in m.name and m.supported_generation_methods and "generateContent" in m.supported_generation_methods:
                model_id = m.name.replace("models/", "")
                return model_id
    except Exception as e:
        print(f"Auto-detect model error: {e}")
    
    return "gemini-2.5-flash"
# --------------------------------------------------------

# --- ระบบความจำบทสนทนารูปแบบข้อความต่อข้อความ พร้อมระบุตัวตน ---
user_histories = defaultdict(lambda: deque(maxlen=6))

def build_prompt_with_history(user_id, new_message):
    history = user_histories[user_id]
    prompt_parts = []
    
    # เช็คว่าเป็นไอดีของคุณหรือไม่ เพื่อระบุสถานะพิเศษให้ AI รู้ทันที
    if user_id == OWNER_DISCORD_ID:
        prompt_parts.append("[ระบบแจ้งเตือนภายใน: คนที่กำลังคุยด้วยอยู่นี้คือ 'พี่ชายสุดที่รักและรู้ใจที่สุด' ของซีมิระ ให้แสดงท่าทีอ้อน กวน หรือสนิทสนมเป็นพิเศษทันที]")
    else:
        prompt_parts.append(f"[ระบบแจ้งเตือนภายใน: คนที่กำลังคุยด้วยคือ User ID: {user_id}]")

    # รวมประวัติเก่าเข้ามาในรูปแบบบทสนทนาต่อกัน
    for speaker, text in history:
        if speaker == "user":
            prompt_parts.append(f"พี่ชาย: {text}" if user_id == OWNER_DISCORD_ID else f"ผู้ใช้: {text}")
        else:
            prompt_parts.append(f"ซีมิระ: {text}")
            
    # ใส่ข้อความล่าสุดเข้าไปท้ายสุด
    prompt_parts.append(f"พี่ชาย: {new_message}" if user_id == OWNER_DISCORD_ID else f"ผู้ใช้: {new_message}")
    prompt_parts.append("ซีมิระ: ") # ไกด์ให้ AI รู้ว่าถึงตาตัวเองตอบ
    
    return "\n".join(prompt_parts)
# ----------------------------------------------------

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

        response = None
        current_model = get_latest_flash_model()
        print(f"Using Model: {current_model}")

        user_id = message.author.id
        final_prompt = build_prompt_with_history(user_id, message.content)

        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=current_model,
                    contents=final_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        temperature=0.9,
                    )
                )
                if response and hasattr(response, 'text') and response.text:
                    break
            except Exception as retry_err:
                print(f"Attempt {attempt + 1} failed: {retry_err}")
                if attempt < max_retries - 1:
                    time.sleep(1.5)
                else:
                    raise retry_err

        try:
            if response and hasattr(response, 'text') and response.text:
                reply_text = response.text.strip()
                
                # บันทึกประวัติเก็บไว้
                user_histories[user_id].append(("user", message.content))
                user_histories[user_id].append(("model", reply_text))

                if len(reply_text) <= 2000:
                    await thinking_msg.edit(content=reply_text)
                else:
                    chunks = [reply_text[i:i+2000] for i in range(0, len(reply_text), 2000)]
                    await thinking_msg.edit(content=chunks[0])
                    for chunk in chunks[1:]:
                        await message.channel.send(chunk)
            else:
                await thinking_msg.edit(content='(ทำหน้าเลิกลั่ก)\n"เอ๊ะ... เหมือนหนูจะนึกไม่ออก เอาใหม่อีกทีนะพี่!"')
                
        except Exception as e:
            error_msg = str(e)
            print(f"DEBUG ERROR: {error_msg}")
            await thinking_msg.edit(content=random.choice(error_phrases))

    except Exception as outer_e:
        print(f"MESSAGE EVENT ERROR: {outer_e}")
        try:
            await message.channel.send(random.choice(error_phrases))
        except:
            pass

TOKEN = os.environ.get("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("Error: DISCORD_TOKEN not found in environment variables.")
