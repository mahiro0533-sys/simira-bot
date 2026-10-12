import asyncio
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

# --- กำหนดไอดีห้องที่อนุญาตส่งข้อความตอบกลับในเซิร์ฟเวอร์ ---
ALLOWED_CHANNEL_ID = 1559088513222316102

# --- ตัวแปรและค่าคงที่สำหรับระบบ AFK (Manual Toggle) ---
is_afk = False
afk_reason = ""

AFK_PRESETS = {
    "1": "(ทำหน้ามุ่ยเบะปาก) \"ตอนนี้พี่ชายกำลังเล่นเกมอยู่นะ! อย่าเพิ่งมากวนล่ะ เดี๋ยวพี่เขาแพ้ขึ้นมาหนูไม่รู้ด้วยนะ ฝากข้อความไว้ก่อนได้เลย!\"",
    "2": "(กอดอกทำหน้าจริงจัง) \"พี่ชายกำลังยุ่งสุดๆ อยู่น่ะสิ! มีเรื่องอะไรด่วนไหม? ฝากเรื่องไว้ก่อนได้เลย เดี๋ยวพอพี่เขาว่างหนูจะรีบสะกิดบอกให้!\"",
    "3": "(เอานิ้วชี้แตะปากทำเสียง ชู้ว์...) \"เบาๆ หน่อยสิ! ตอนนี้พี่ชายกำลังนอนพักผ่อนอยู่นะ อย่าเพิ่งมาส่งเสียงดังรบกวนล่ะ มีอะไรก็ทิ้งข้อความไว้ได้เลย!\""
}
# ----------------------------------------------------

# --- ระบบอัปเดตโมเดลอัตโนมัติและสแกนหาตัวสำรองอัจฉริยะ ---
def get_latest_flash_model():
    available_models = []
    try:
        for m in client.models.list():
            if "flash" in m.name and m.supported_generation_methods and "generateContent" in m.supported_generation_methods:
                clean_name = m.name.replace("models/", "")
                available_models.append(clean_name)
        
        if available_models:
            latest_model = available_models[0]
            print(f"Auto-detected active flash model: {latest_model}")
            return latest_model
            
    except Exception as e:
        print(f"Auto-detect model error: {e}")
    
    fallback_model = "gemini-3.6-flash"
    print(f"Using dynamic fallback model: {fallback_model}")
    return fallback_model
# --------------------------------------------------------

# ตั้งค่าคาแรคเตอร์น้องซีมิระ
SYSTEM_INSTRUCTION = """
คุณคือ "ซีมิระ" (Simira) บอทสาวน้อยขี้เล่น สดใส กวนๆ และติดพี่ชายมากๆ กำลังแชทคุยเล่นอย่างอิสระใน Discord
กฎในการตอบ:
1. ห้ามใช้ EMOJI หรืออีโมจิเด็ดขาด
2. ตอบให้สั้น กระชับ เป็นกันเอง เป็นธรรมชาติตามบทสนทนาจริง
3. ทำท่าทางหรืออารมณ์ให้อยู่ในวงเล็บ ( ) เสมอ เช่น (หรี่ตามมอง), (กอดอกยิ้มกวนๆ)
4. คำพูดบทสนทนาให้อยู่ในเครื่องหมายคำพูด "..."
5. **การตอบโต้แบบอิสระ:**
   - อ่านสไตล์การพิมพ์และอารมณ์ของผู้ใช้ แล้วตอบกลับไปตามน้ำได้เลยทันที ไม่ว่าจะกวนมา กวนกลับ ปะทะมุก หรือคุยเล่นทั่วไป
   - โต้ตอบอย่างลื่นไหลเหมือนคนจริงๆ คุยกันใน Discord
"""

# --- จัดการเซสชันแชทแยกตามรายบุคคล ---
user_chats = {}

def get_or_create_chat(user_id, model_name):
    if user_id not in user_chats:
        initial_history = []
        if user_id == OWNER_DISCORD_ID:
            initial_history = [
                types.Content(role="user", parts=[types.Part.from_text(text="[ระบบภายใน: คุยกับ 'พี่ชายสุดที่รัก' ให้แสดงท่าทีอ้อน กวน สนิทสนมเป็นพิเศษ]")]),
                types.Content(role="model", parts=[types.Part.from_text(text='(ยิ้มแป้นวิ่งเข้าไปเกาะแขน)\n"รู้แล้วน่า! ก็พี่ชายคนโปรดของหนูคนนี้นี่นา มีอะไรเหรอถึงมาหาหนูเนี่ย?"')])
            ]
        else:
            initial_history = [
                types.Content(role="user", parts=[types.Part.from_text(text="[ระบบภายใน: คุยกับสมาชิกในเซิร์ฟเวอร์ (ไม่ใช่พี่ชาย) ห้ามเรียกว่าพี่ ให้พูดคุยโต้ตอบกวนๆ หรือตามน้ำตามสไตล์ของคู่สนทนาได้อย่างอิสระเสรี]")])
            ]
        
        chat = client.chats.create(
            model=model_name,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.95,  # เพิ่มความคิดสร้างสรรค์ให้ตอบได้อย่างอิสระยิ่งขึ้น
            ),
            history=initial_history
        )
        user_chats[user_id] = chat
    return user_chats[user_id]
# -----------------------------------------------------------------

thinking_phrases = [
    '⏳ (ทำหน้ามุ่ยใส่จอ)\n"เดี๋ยวสิ! ขอเวลาอ่านแป๊บ..."',
    '🔄 (เอียงคอสงสัย)\n"อืม... ขอคิดดูก่อนแป๊บหนึ่ง!"',
    '💬 (กอดอกพึมพำ)\n"แป๊บนะ กำลังคิดอยู่..."',
    '✨ (หรี่ตามมองจอ)\n"เดี๋ยวๆ ขออ่านแชทแป๊บ"'
]

error_phrases = [
    '(กุมขมับส่ายหัว)\n"โอ๊ย ปวดหัวชะมัด เซิร์ฟเวอร์รวนหมดแล้วเนี่ย!"',
    '(ขยี้หัวตัวเองหงุดหงิด)\n"สมองหนูจะระเบิดแล้วนะ!"',
    '(ถอนหายใจแรงๆ)\n"อะไรเนี่ย ระบบรวนไปหมดเลย ชิ!"'
]

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"น้องซีมิระพร้อมลุยแล้วจ้า! (Logged in as {bot.user})")

# ฟังก์ชันช่วยเปิด AFK
async def enable_afk(ctx, option: str):
    global is_afk, afk_reason
    if option in AFK_PRESETS:
        afk_reason = AFK_PRESETS[option]
    else:
        afk_reason = f'(เอียงคอน้อยๆ) "ตอนนี้พี่ชายติดภารกิจ: \'{option}\' อยู่น่ะสิ! มีอะไรฝากข้อความไว้ได้เลย เดี๋ยวหนูไปบอกให้!"'
    
    is_afk = True
    await ctx.send('(พยักหน้ารับคำสั่งอย่างแข็งขัน)\n"รับทราบค่ะพี่! เดี๋ยวหนูดูหน้าจอให้นะ พี่ไปพักผ่อนได้เลย!"')

# --- คำสั่งเปิด AFK หลัก ---
@bot.command(name="afk")
async def afk_command(ctx, option: str = "2"):
    await enable_afk(ctx, option)

# --- คำสั่งลัดสำเร็จรูป (!afk1, !afk2, !afk3) ---
@bot.command(name="afk1")
async def afk1_command(ctx):
    await enable_afk(ctx, "1")

@bot.command(name="afk2")
async def afk2_command(ctx):
    await enable_afk(ctx, "2")

@bot.command(name="afk3")
async def afk3_command(ctx):
    await enable_afk(ctx, "3")

# --- คำสั่งสำหรับปิด AFK (ต้องพิมพ์ !unafk เท่านั้น) ---
@bot.command(name="unafk")
async def unafk_command(ctx):
    global is_afk, afk_reason
    if is_afk:
        is_afk = False
        afk_reason = ""
        await ctx.send('(ยิ้มแป้นวิ่งเข้าไปหา)\n"ยินดีต้อนรับกลับมาค่ะพี่ชาย! หนูปลดโหมด AFK ให้เรียบร้อยแล้วน้า~"')
    else:
        await ctx.send('(เอียงคอสงสัย)\n"พี่ไม่ได้เปิดโหมด AFK ไว้สักหน่อยนี่นา!"')

@bot.event
async def on_message(message):
    global is_afk, afk_reason

    try:
        # ห้ามบอทตอบตัวเอง
        if message.author == bot.user:
            return

        # ตรวจสอบข้อความคำสั่งบอทก่อน
        ctx = await bot.get_context(message)
        if ctx.valid:
            await bot.process_commands(message)
            return

        is_dm = isinstance(message.channel, discord.DMChannel)

        # --- 1. ระบบ AFK: ตรวจจับคนแท็กพี่ชายจากทุกห้อง / ทุก DM ---
        if is_afk:
            is_owner_mentioned = (bot.user in message.mentions) or (f"<@{OWNER_DISCORD_ID}>" in message.content) or (str(OWNER_DISCORD_ID) in message.content)
            
            if (is_dm or is_owner_mentioned) and message.author.id != OWNER_DISCORD_ID:
                await asyncio.sleep(30)
                
                if is_afk:
                    target_channel = bot.get_channel(ALLOWED_CHANNEL_ID)
                    if target_channel:
                        await target_channel.send(f"{message.author.mention} {afk_reason}")
                return

        # --- 2. ระบบ AI คุยเล่นปกติ: ให้คุยเฉพาะใน DM หรือ ในห้องที่กำหนดเท่านั้น ---
        if not is_dm and message.channel.id != ALLOWED_CHANNEL_ID:
            return

        if not message.content or not message.content.strip():
            return

        thinking_msg = await message.channel.send(random.choice(thinking_phrases))

        current_model = get_latest_flash_model()
        print(f"Using Model: {current_model}")

        user_id = message.author.id
        chat_session = get_or_create_chat(user_id, current_model)

        # ปลดล็อกข้อความ ส่งข้อความจริงของผู้ใช้เข้าไปให้ AI คิดคำตอบแบบอิสระทันที
        prompt_to_send = message.content

        response = None
        max_retries = 2
        for attempt in range(max_retries):
            try:
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
            await thinking_msg.edit(content='(ทำหน้าเลิกลั่ก)\n"เอ๊ะ... เหมือนหนูจะนึกไม่ออก เอาใหม่อีกทีนะ!"')

    except Exception as outer_e:
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
