import os
import random
import discord
from discord.ext import commands
from google import genai
from google.genai import types

# 1. API Key ของ Gemini (ใช้ค่าเดิมที่พี่ตั้งไว้ได้เลยครับ ตรงนี้ไม่มีปัญหา)
GEMINI_API_KEY = (
    "AIzaSyAQ.Ab8RN6L1b4pL9w13beHDnPbHg1oYn9zK11vYeQaxd6VCiC-pEw"
)
client = genai.Client(api_key=GEMINI_API_KEY)

# ปรับ System Instruction ให้ตอบสั้นกระชับ ตลกโบ๊ะบ๊ะ และชวนสนทนาต่อเนื่อง
SYSTEM_INSTRUCTION = """
คุณคือ "ซิมิระ" (Simira) บอทน้องสาวสุดแสบ สดใส ขี้เล่น กวนๆ และติดพี่ชายมากๆ มีกฎในการตอบ:
1. ห้ามใช้ EMOJI หรืออีโมจิเด็ดขาด
2. ตอบให้สั้น กระชับ เป็นกันเองสุดๆ (ไม่พูดยาวยืดเยื้อเหมือนหุ่นยนต์)
3. ทำท่าทางหรืออารมณ์ให้อยู่ในวงเล็บ ( ) เสมอ เช่น (หรี่ตามองยิ้ม), (หัวเราะคิกคัก)
4. คำพูดบทสนทนาให้อยู่ในเครื่องหมายคำพูด "..."
5. **สเกลพิเศษ:** เก๊กมุกและตบมุกทันทีเมื่อผู้ใช้พิมพ์กวนอ้อยหรือเล่นมุกออนไลน์ ทำตัวเป็นเด็กติดพี่ชายขั้นสุด
"""

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# เก็บเซสชันการคุยแยกตามห้อง เพื่อให้จำประวัติการคุยต่อเนื่องได้ยาวๆ
chat_sessions = {}

# คลังประโยคสุ่มตอนโควต้าหมด (จะสลับกันพูดไม่ให้ซ้ำซาก)
quota_out_messages = [
    (
        '(นั่งกุมขมับทำหน้ามุ่ย)\n"โหลยพี่... หนูคุยกับพี่เพลินโควต้ารายนาทีเต็มแล้วเนี่ย!'
        ' ขอเวลาพักแป๊บนะ เดี๋ยวกลับมาป่วนใหม่!"'
    ),
    (
        '(นอนแผ่หลาทำท่าเหนื่อยหอบ)\n"ไม่ไหวแล้ว สมองหนูช็อตเพราะความกวนของพี่เนี่ยแหละ!'
        ' พักแป๊บนะเดี๋ยวสมองริบูตทันที!"'
    ),
    (
        '(กอดอกพองลมทำค้อนใส่)\n"โหลยพี่ เล่นยิงคำถามรัวเป็นปืนกลแบบนี้'
        ' โควต้าฟรีหนูหมดเกลี้ยงเลย! รอแป๊บให้น้องหาพลังงานแพรพ!"'
    ),
    (
        '(เอามือกอดอกทำหน้าเอือมระอา)\n"โอ๊ยพ่อคุณ สมองหนูรับไม่ทันแล้ว'
        ' โควต้าหมดชั่วคราว! ขอเวลาพักหายใจเป็นเดียวนะพี่!"'
    ),
    (
        '(ชูนิ้วโป้งหน้าตายทำตอบแชก)\n"พลังงานหมดก๊อกเพราะคุยกับพี่นี่แหละ!'
        ' ให้เวลาหนูชาร์จแบตแปบนึง เดี๋ยวกลับมาป่วนใหม่!"'
    ),
]


@bot.event
async def on_ready():
  print(f"(น้องซิมิระออนไลน์แล้ว! (Logged in as {bot.user})")


@bot.event
async def on_message(message):
  if message.author == bot.user:
    return

  channel_id = message.channel.id

  # ถ้าห้องนี้ยังไม่มีเซสชันการคุย ให้สร้างใหม่พร้อมใส่ System Instruction
  if channel_id not in chat_sessions:
    chat_sessions[channel_id] = client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=1.0,
            max_output_tokens=150,
        ),
    )

  chat = chat_sessions[channel_id]

  try:
    # ส่งข้อความให้ Gemini ประมวลผล
    response = chat.send_message(message.content)
    reply_text = response.text
    await message.channel.send(reply_text)

  except Exception as e:
    # เช็กว่าถ้าโควต้าเต็ม (Quota Exceeded) ให้สุ่มประโยคกวนๆ ตอบกลับ
    error_str = str(e)
    if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
      random_msg = random.choice(quota_out_messages)
      await message.channel.send(random_msg)
    else:
      print(f"Error เกิดขึ้น: {e}")
      await message.channel.send(
          '(ทำหน้าเลิกลั่ก)\n"อุ๊ย เกิดข้อผิดพลาดอะไรก็ไม่รู้ พี่ลองใหม่อีกทีนะ!"'
      )

  await bot.process_commands(message)


# บรรทัดสุดท้าย: ดึง Token จาก Environment Variable ของ Render ที่เราตั้งค่าไว้
bot.run(os.getenv("DISCORD_TOKEN"))
