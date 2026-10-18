import asyncio
import logging
import os
import google.generativeai as genai
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv
from database import init_db, save_calculation, get_history

load_dotenv()
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🧮 حل مسألة"), KeyboardButton(text="📝 اختبرني")],
        [KeyboardButton(text="💾 سجلي"), KeyboardButton(text="ℹ️ مساعدة")]
    ],
    resize_keyboard=True
)

async def ask_gemini(prompt):
    try:
        response = await model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        logging.error(f"Gemini Error: {e}")
        return "⚠️ عذراً، حدث خطأ في الاتصال بالذكاء الاصطناعي."

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("أهلاً بك في **معلم الرياضيات الذكي**! 🧠🧮\n\nاختر من الأزرار تحت 👇", reply_markup=keyboard, parse_mode="Markdown")

@dp.message(F.text == "ℹ️ مساعدة")
async def cmd_help(message: types.Message):
    await message.answer("اكتب أي مسألة رياضية وسأشرحها لك خطوة بخطوة، أو اضغط 'اختبرني' لتجربة سؤال.", reply_markup=keyboard)

@dp.message(F.text == "💾 سجلي")
async def cmd_history(message: types.Message):
    history = await get_history(message.from_user.id, limit=5)
    if not history:
        await message.answer("📭 سجلك فارغ حالياً.")
        return
    text = "📊 **آخر 5 عمليات لك:**\n\n"
    for item in history:
        text += f"🔹 `{item['expression']}` = **{item['result']}**\n"
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "🧮 حل مسألة")
async def ask_math(message: types.Message):
    await message.answer("✍️ اكتب المسألة الآن:")

@dp.message(F.text == "📝 اختبرني")
async def test_me(message: types.Message):
    await message.answer("⏳ جاري تحضير سؤال...")
    question = await ask_gemini("أعطني سؤالاً رياضياً واحداً فقط بدون الحل.")
    await message.answer(f"📝 **سؤالي:**\n\n{question}\n\nاكتب إجابتك:")

@dp.message(F.text)
async def handle_text(message: types.Message):
    text = message.text.strip()
    if text in ["🧮 حل مسألة", "📝 اختبرني", "ℹ️ مساعدة", "💾 سجلي"]:
        return
    await message.answer("⏳ جاري التفكير...")
    prompt = f"أنت معلم رياضيات. المستخدم أرسل: '{text}'. إذا كانت مسألة، حلها واشرح خطواتها بالعربي. إذا كانت إجابة، صححها."
    response_text = await ask_gemini(prompt)
    await message.answer(response_text)
    await save_calculation(message.from_user.id, message.from_user.username or "Unknown", "ai_math", text, "تم الحل", [])

# --- هذا الجزء الجديد عشان نرضي Render ---
async def health_check(request):
    return web.Response(text="OK")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Web server started on port {port}")
# ------------------------------------------

async def main():
    await init_db()
    await start_web_server() # تشغيل السيرفر الوهمي
    print("🚀 البوت شغال...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
