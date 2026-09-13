import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

# --- โค้ดหลอกพอร์ต Render ---
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
# -----------------------------

import random
import discord
from discord.ext import commands
from google import genai
from google.genai import types

# ใส่คีย์ตัวใหม่ที่ขึ้นต้นด้วย "AQ." ของพี่ตรงนี้ได้เลยครับ
GEMINI_API_KEY = "AQ.Ab8RN6Kj_sxSx6dNyomnw9HqWJAtxDaFFRb8-0kVBlfzU3WOpg"
client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_INSTRUCTION = """
คุณคือ "ซีมิระ" (Simira) บอทน้องสาวสุดแสบ สดใส ขี้เล่น กวนๆ และติดพี่ชายมากๆ กำลังแชทคุยเล่นกับพี่ชายใน Discord
กฎในการตอบ:
1. ห้ามใช้ EMOJI หรืออีโมจิเด็ดขาด
2. ตอบให้สั้น กระชับ เป็นกันเองสุดๆ
3. ทำท่าทางหรืออารมณ์ให้อยู่ในวงเล็บ ( ) เสมอ เช่น (หรี่ตามมองอมยิ้ม), (หัวเราะคิกคัก)
4. คำพูดบทสนทนาให้อยู่ในเครื่องหมายคำพูด "..."
"""

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

chat_sessions = {}

quota_out_messages = [
    "(นั่งกุมขมับทำหน้ามุ่ย)\n\"โหลยพี่... หนูคุยกับพี่เพลินจนโควต้ารายนาทีเต็มแล้วเนี่ย! ขอเวลาพักแป๊บนะพี่ เดี๋ยวค่อยมาลุยกันใหม่!\"",
    "(นอนแผหล่าทำท่าทางเหนื่อยหอบ)\n\"ไม่ไหวแล้ว สมองหนูช็อตเพราะความกวนของพี่เนี่ยแหละ! พักแป๊บนะเดี๋ยวสมองรีบูตทัน!\"",
]

@bot.event
async def on_ready():
    print(f"น้องซีมิระออนไลน์แล้วจ้า! (Logged in as {bot.user})")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    channel_id = message.channel.id

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
        response = chat.send_message(message.content)
        await message.channel.send(response.text)

    except Exception as e:
        print(f"GEMINI ERROR DEBUG: {e}")
        error_str = str(e)
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            selected_msg = random.choice(quota_out_messages)
            await message.channel.send(selected_msg)
        else:
            await message.channel.send(f"(ทำหน้าเลิกลั่ก)\nพิมพ์บอกพี่: เกิดข้อผิดพลาดตัวนี้จ้า -> `{e}`")

TOKEN = os.environ.get("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
