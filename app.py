import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv
from google import genai

from database import init_db, save_calculation, get_history

load_dotenv()
logging.basicConfig(level=logging.INFO)

# جلب المفاتيح
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# إعداد Gemini بالمكتبة الجديدة
client = genai.Client(api_key=GEMINI_KEY)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# الأزرار
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🧮 حل مسألة"), KeyboardButton(text="📝 اختبرني")],
        [KeyboardButton(text="💾 سجلي"), KeyboardButton(text="ℹ️ مساعدة")]
    ],
    resize_keyboard=True
)

# دالة التحدث مع Gemini
async def ask_gemini(prompt):
    try:
        # استخدام الموديل الجديد الذي يدعم مفاتيح AQ
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=prompt,
        )
        return response.text
    except Exception as e:
        logging.error(f"Gemini Error: {e}")
        return "⚠️ عذراً، حدث خطأ في الاتصال بالذكاء الاصطناعي."

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "أهلاً بك في **معلم الرياضيات الذكي**! 🧠🧮\n\n"
        "اختر من الأزرار تحت 👇 أو اكتب مسألتك مباشرة.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.message(F.text == "ℹ️ مساعدة")
async def cmd_help(message: types.Message):
    await message.answer(
        "• اكتب أي مسألة مثل `2x+5=15` أو `جذر 144` وسأشرح لك الحل.\n"
        "• اضغط 'اختبرني' لتجربة سؤال.\n"
        "• اضغط 'سجلي' لمشاهدة آخر عملياتك.",
        reply_markup=keyboard
    )

@dp.message(F.text == "💾 سجلي")
async def cmd_history(message: types.Message):
    history = await get_history(message.from_user.id, limit=5)
    if not history:
        await message.answer("📭 سجلك فارغ حالياً. جرب حل مسألة أولاً!")
        return
    text = "📊 **آخر 5 عمليات لك:**\n\n"
    for item in history:
        text += f"🔹 `{item['expression']}` = **{item['result']}**\n"
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "🧮 حل مسألة")
async def ask_math(message: types.Message):
    await message.answer("✍️ اكتب المسألة الآن، وسأشرح لك الحل خطوة بخطوة:")

@dp.message(F.text == "📝 اختبرني")
async def test_me(message: types.Message):
    await message.answer("⏳ جاري تحضير سؤال...")
    prompt = "أنت معلم رياضيات. أعطني سؤالاً رياضياً واحداً فقط (بدون الحل) مناسباً لمستوى طالب متوسط. اجعل السؤال قصيراً ومباشراً."
    question = await ask_gemini(prompt)
    await message.answer(f"📝 **سؤالي لك:**\n\n{question}\n\nاكتب إجابتك الآن:")

@dp.message(F.text)
async def handle_text(message: types.Message):
    text = message.text.strip()
    
    if text in ["🧮 حل مسألة", "📝 اختبرني", "ℹ️ مساعدة", "💾 سجلي"]:
        return

    await message.answer("⏳ جاري التفكير...")
    
    prompt = f"""
    أنت معلم رياضيات ذكي ومحترف. 
    المستخدم أرسل لك هذه الرسالة: "{text}"
    
    إذا كانت مسألة رياضية: قم بحلها واشرح الخطوات بالتفصيل وبطريقة بسيطة ومفهومة باللغة العربية.
    إذا كانت إجابة على سؤال سابق: صحح الإجابة (صح أم خطأ) واشرح السبب.
    إذا كانت رسالة عادية: رد عليها بود واقترح مساعدة في الرياضيات.
    
    اجعل الرد منظماً ومقروءاً.
    """
    
    response_text = await ask_gemini(prompt)
    await message.answer(response_text, parse_mode="Markdown")
    
    await save_calculation(
        user_id=message.from_user.id,
        username=message.from_user.username or "Unknown",
        category="ai_math",
        expression=text,
        result="تم الحل بواسطة AI",
        steps=[]
    )

# --- جزء Keep-Alive عشان Render ما يطفي البوت ---
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
    print(f"✅ Web server started on port {port}")

async def main():
    await init_db()
    
    # تنظيف أي اتصال قديم (عشان نمنع مشكلة Conflict)
    await bot.delete_webhook(drop_pending_updates=True)
    
    # تشغيل سيرفر الويب (لإرضاء Render)
    await start_web_server()
    
    print("🚀 البوت شغال الآن...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
