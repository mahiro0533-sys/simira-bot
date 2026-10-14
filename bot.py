import asyncio
import os
import random
import time
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

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY not found in environment variables.")

client = genai.Client(api_key=GEMINI_API_KEY)

# ไอดีเจ้าของบอท (พี่ชาย)
OWNER_DISCORD_ID = 1515771398688084008

# 🎯 **กำหนดหน้าที่ของแต่ละห้องให้ชัดเจน:**
AI_CHAT_CHANNEL_ID = 1559088513222316102   # ห้องคุยเล่นกับ AI (ให้น้องตอบคุยเล่นได้)
MAIN_TALK_CHANNEL_ID = 1557629870534692905 # ห้องพูดคุยหลัก (อ่านดักจับเฉพาะคนแท็กชื่อพี่ชายตอนเปิด AFK เท่านั้น ห้าม AI คุยเล่นเด็ดขาด!)

ALLOWED_CHANNEL_IDS = [AI_CHAT_CHANNEL_ID, MAIN_TALK_CHANNEL_ID]

# --- ระบบสแกนหาโมเดลอัตโนมัติ "แค่รอบเดียวตอนเปิดเครื่อง" (ระบบเดิมที่พี่ชายตั้งไว้) ---
ACTIVE_MODEL = "gemini-2.5-flash" # ค่าสำรองฉุกเฉินเริ่มต้น

def detect_best_model_once():
    global ACTIVE_MODEL
    try:
        available_models = []
        for m in client.models.list():
            if "flash" in m.name and m.supported_generation_methods and "generateContent" in m.supported_generation_methods:
                clean_name = m.name.replace("models/", "")
                available_models.append(clean_name)
        
        if available_models:
            ACTIVE_MODEL = available_models[0]
            print(f"🚀 [Startup] Auto-detected best flash model: {ACTIVE_MODEL}")
    except Exception as e:
        print(f"⚠️ Auto-detect model warning: {e}, using default: {ACTIVE_MODEL}")

detect_best_model_once()
# ------------------------------------------------------------------------------

is_afk = False
afk_reason = ""

AFK_PRESETS = {
    "1": "(ทำหน้ามุ่ยเบะปาก) \"ตอนนี้พี่ชายกำลังเล่นเกมอยู่นะ! อย่าเพิ่งมากวนล่ะ เดี๋ยวพี่เขาแพ้ขึ้นมาหนูไม่รู้ด้วยนะ ฝากข้อความไว้ก่อนได้เลย!\"",
    "2": "(กอดอกทำหน้าจริงจัง) \"พี่ชายกำลังยุ่งสุดๆ อยู่น่ะสิ! มีเรื่องอะไรด่วนไหม? ฝากเรื่องไว้ก่อนได้เลย เดี๋ยวพอพี่เขาว่างหนูจะรีบสะกิดบอกให้!\"",
    "3": "(เอานิ้วชี้แตะปากทำเสียง ชู้ว์...) \"เบาๆ หน่อยสิ! ตอนนี้พี่ชายกำลังนอนพักผ่อนอยู่นะ อย่าเพิ่งมาส่งเสียงดังรบกวนล่ะ มีอะไรก็ทิ้งข้อความไว้ได้เลย!\""
}

SYSTEM_INSTRUCTION = """
คุณคือ "ซีมิระ" (Simira) บอทสาวน้อยขี้เล่น สดใส กวนๆ และติดพี่ชายมากๆ กำลังแชทคุยเล่นอย่างอิสระใน Discord
กฎในการตอบ:
1. ห้ามใช้ EMOJI หรืออีโมจิเด็ดขาด
2. ตอบให้สั้น กระชับ เป็นกันเอง เป็นธรรมชาติตามบทสนทนาจริง
3. ทำท่าทางหรืออารมณ์ให้อยู่ในวงเล็บ ( ) เสมอ เช่น (หรี่ตามมอง), (กอดอกยิ้มกวนๆ)
4. คำพูดบทสนทนาให้อยู่ในเครื่องหมายคำพูด "..."
5. **การตอบโต้แบบอิสระ:**
   - อ่านสไตล์การพิมพ์และอารมณ์ของผู้ใช้ แล้วตอบกลับไปตามน้ำได้เลยทันที ไม่ว่าจะกวนมา กวนกลับ ปะทะมุก หรือคุยเล่นทั่วไป
"""

user_chats = {}

def get_or_create_chat(user_id):
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
            model=ACTIVE_MODEL,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.95,
            ),
            history=initial_history
        )
        user_chats[user_id] = chat
    return user_chats[user_id]

thinking_phrases = [
    '⏳ (ทำหน้ามุ่ยใส่จอ)\n"เดี๋ยวสิ! ขอเวลาอ่านแป๊บ..."',
    '🔄 (เอียงคอสงสัย)\n"อืม... ขอคิดดูก่อนแป๊บหนึ่ง!"',
    '💬 (กอดอกพึมพำ)\n"แป๊บนะ กำลังคิดอยู่..."',
    '✨ (หรี่ตามมองจอ)\n"เดี๋ยวๆ ขออ่านแชทแป๊บ"'
]

error_phrases = [
    '(เบะปากทำหน้าเซ็ง)\n"สมองหนูช็อตไปนิดนึง เอาใหม่อีกทีนะพี่!"'
]

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"น้องซีมิระพร้อมลุยแล้วจ้า! (Logged in as {bot.user}) | ใช้โมเดล: {ACTIVE_MODEL}")

async def enable_afk(ctx, option: str):
    global is_afk, afk_reason
    if option in AFK_PRESETS:
        afk_reason = AFK_PRESETS[option]
    else:
        afk_reason = f'(เอียงคอน้อยๆ) "ตอนนี้พี่ชายติดภารกิจ: \'{option}\' อยู่น่ะสิ! มีอะไรฝากข้อความไว้ได้เลย เดี๋ยวหนูไปบอกให้!"'
    
    is_afk = True
    await ctx.send('(พยักหน้ารับคำสั่งอย่างแข็งขัน)\n"รับทราบค่ะพี่! เดี๋ยวหนูดูหน้าจอให้นะ พี่ไปพักผ่อนได้เลย!"')

@bot.command(name="afk")
async def afk_command(ctx, option: str = "2"):
    await enable_afk(ctx, option)

@bot.command(name="afk1")
async def afk1_command(ctx):
    await enable_afk(ctx, "1")

@bot.command(name="afk2")
async def afk2_command(ctx):
    await enable_afk(ctx, "2")

@bot.command(name="afk3")
async def afk3_command(ctx):
    await enable_afk(ctx, "3")

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
        # 1. ห้ามบอทตอบตัวเอง
        if message.author == bot.user:
            return

        is_dm = isinstance(message.channel, discord.DMChannel)

        # 2. เช็กห้อง: ถ้าไม่ใช่ DM และไม่ได้อยู่ในห้องที่อนุญาต -> ตัดจบตั้วแต่วินาทีแรก (Early Exit)
        if not is_dm and message.channel.id not in ALLOWED_CHANNEL_IDS:
            return

        # 3. เช็กคำสั่งบอททั่วไป (!afk, !unafk)
        ctx = await bot.get_context(message)
        if ctx.valid:
            await bot.process_commands(message)
            return

        user_id = message.author.id
        is_owner_mentioned = (bot.user in message.mentions) or (f"<@{OWNER_DISCORD_ID}>" in message.content) or (str(OWNER_DISCORD_ID) in message.content)

        # 4. ระบบ AFK: ดักจับเฉพาะตอนเปิด AFK แล้ว "มีคนมาแท็กชื่อพี่ชาย" เท่านั้น
        if is_afk and (is_dm or is_owner_mentioned) and user_id != OWNER_DISCORD_ID:
            await asyncio.sleep(15)
            if is_afk:
                await message.channel.send(f"{message.author.mention} {afk_reason}")
            return # ตอบข้อความ AFK เสร็จปุ๊บ ตัดจบการทำงานทันที!

        # 🎯 **5. ล็อคเป้าห้องพูดคุยหลัก (MAIN_TALK_CHANNEL_ID):**
        # ถ้าข้อความมาจากห้องนี้ และไม่ใช่ระบบ AFK ด้านบน -> "ตัดจบการทำงานทันที ห้าม AI ตอบคุยเล่นเด็ดขาด!"
        if not is_dm and message.channel.id == MAIN_TALK_CHANNEL_ID:
            return

        if not message.content or not message.content.strip():
            return

        # 6. กระบวนการคุยกับ AI (จะเกิดขึ้นเฉพาะในห้อง AI_CHAT_CHANNEL_ID หรือ DM เท่านั้น!)
        thinking_msg = await message.channel.send(random.choice(thinking_phrases))

        response = None
        max_retries = 2
        for attempt in range(max_retries):
            try:
                chat_session = get_or_create_chat(user_id)
                response = chat_session.send_message(message.content)
                if response and hasattr(response, 'text') and response.text:
                    break
            except Exception as retry_err:
                print(f"Attempt {attempt + 1} failed: {retry_err}")
                if user_id in user_chats:
                    del user_chats[user_id]
                if attempt < max_retries - 1:
                    await asyncio.sleep(1.0)
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
            await thinking_msg.edit(content='(ทำหน้าเลิกลั่ก)\n"เอ๊ะ... เหมือนหนูจะนึกไม่ออก เอาใหม่อีกทีนะ!"')

    except Exception as outer_e:
        print(f"MESSAGE EVENT ERROR DETECTED: {str(outer_e)}")
        if 'user_id' in locals() and user_id in user_chats:
            del user_chats[user_id]
        try:
            await message.channel.send(random.choice(error_phrases))
        except:
            pass

TOKEN = os.environ.get("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("Error: DISCORD_TOKEN not found in environment variables.")
