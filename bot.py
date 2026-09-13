import random
import discord
from discord.ext import commands
from google import genai
from google.genai import types

# 1. API Key ของคุณ
GEMINI_API_KEY = (
    "AQ.Ab8RN6Llb4pL9w13beHDnPbHg1oYn9zK1lvYeQaxd6VCiC-pEw"
)
client = genai.Client(api_key=GEMINI_API_KEY)

# ปรับ System Instruction ให้ตอบสั้นกระชับ ตบมุกโบ๊ะบ๊ะ และจำบทสนทนาต่อเนื่อง
SYSTEM_INSTRUCTION = """
คุณคือ "ซีมิระ" (Simira) บอทน้องสาวสุดแสบ สดใส ขี้เล่น กวนๆ และติดพี่ชายมากๆ กำลังแชทคุยเล่นกับผู้ใช้ใน Discord แบบต่อเนื่อง
กฎเหล็กในการตอบ:
1. ห้ามใช้ EMOJI หรืออิโมจิเด็ดขาด
2. ตอบให้สั้น กระชับ เป็นกันเองสุดๆ (ไม่พูดยาวยืดเยื้อเหมือนหุ่นยนต์)
3. ท่าทางหรืออารมณ์ให้อยู่ในวงเล็บ ( ) เสมอ เช่น (หรี่ตามองบนอมยิ้ม), (หัวเราะคิกคักชูนิ้วโป้ง)
4. คำพูดบทสนทนาให้อยู่ในเครื่องหมายคำพูด "..."
5. **สกิลพิเศษ:** เก็ทมุกและตบมุกกลับทันทีเมื่อผู้ใช้พิมพ์กวนโอ๊ยหรือเล่นมุกออนไลน์ ทำตัวเหมือนน้องสาวแท้ๆ ที่รู้ทันพี่ชายทุกเรื่อง
"""

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# เก็บเซสชันการคุยแยกตามห้อง เพื่อให้จำประวัติการคุยต่อเนื่องได้ยาวๆ
chat_sessions = {}

# คลังประโยคสุ่มตอนโควต้าหมด (จะสลับกันพูดไม่ให้ซ้ำซาก)
quota_out_messages = [
    '(นั่งกุมขมับทำหน้ามุ่ย)\n"โหยพี่... หนูคุยกับพี่เพลินจนโควต้ารายนาทีเต็มแล้วเนี่ย! ขอเวลาหนูหายใจสัก 1 นาทีค่อยมาลุยกันต่อ"',
    '(นอนแผ่หลาทำท่าทางเหนื่อยหอบ)\n"ไม่ไหวแล้ว สมองหนูช็อตเพราะความกวนของพี่เนี่ยแหละ! ขอพักแป๊บนะเดี๋ยวมาใหม่"',
    '(กอดอกพองลมทำค้อนใส่)\n"โห่พี่ เล่นยิงคำถามรัวเป็นปืนกลแบบนี้ โควต้าฟรีหนูหมดเกลี้ยงเลยเห็นไหม! รอแป๊บสิคนสวยจะพักผ่อน"',
    '(เอามืองนวดขมับทำหน้าเอือมระอา)\n"โอ๊ยพ่อคุณ สมองหนูรันไม่ทันแล้ว โควต้าหมดชั่วคราวเลยเนี่ย ไปต้มมาม่ากินรอหนูแป๊บเดียวนะ!"',
    '(ชูนิ้วโป้งหน้าตายแต่หอบแฮ่ก)\n"พลังงานหมดก๊อกเพราะคุยกับพี่นี่แหละ ให้เวลาหนูชาร์จแบตแป๊บนึง เดี๋ยวกลับมาตบมุกต่อแน่นอน!"',
]


@bot.event
async def on_ready():
  print(f"หนู {bot.user.name} สมอง AI พร้อมเชื่อมต่อความต่อเนื่องแล้วค่ะ! ✨")


@bot.event
async def on_message(message):
  if message.author == bot.user:
    return

  channel_id = message.channel.id

  if channel_id not in chat_sessions:
    chat_sessions[channel_id] = client.chats.create(
        model="gemini-3.6-flash",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.85,
        ),
    )

  chat = chat_sessions[channel_id]

  async with message.channel.typing():
    try:
      user_message = f"{message.author.display_name}: {message.content}"
      response = chat.send_message(user_message)

      reply_text = response.text
      await message.channel.send(reply_text)

    except Exception as e:
      error_str = str(e)
      print(f"Error: {error_str}")

      # ถ้ารัวข้อความจนโควต้าหมด จะสุ่มเลือกประโยคจากคลังด้านบนมาตอบ
      if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
        random_reply = random.choice(quota_out_messages)
        await message.channel.send(random_reply)
      else:
        await message.channel.send(
            '(เกาหัวทำหน้าเอ๋อเล็กน้อย)\n"เอ๊ะ... มุกเมื่อกี้ทำสมองหนูรวนไปนิด ลองพิมพ์มาใหม่อีกทีนะพี่!"'
        )

  await bot.process_commands(message)


# 2. Token Discord ของบอท
bot.run(
    "MTU0ODMyMTU0MzE3MDMwMjA3OA.GgZfGw.K2X8EvAlQYFQvKNTxw_YAK2XyOEAAlYErlHW_s"
)
