import asyncio
import logging
import os
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

from database import init_db, save_calculation, get_history

load_dotenv()
logging.basicConfig(level=logging.INFO)

# إعداد التوكنات
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# إعداد Gemini
genai.configure(api_key=GEMINI_KEY)
# نستخدم أحدث نموذج سريع ومجاني
model = genai.GenerativeModel('gemini-1.5-flash') 

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# أزرار الكيبورد
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
        response = await model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        logging.error(f"Gemini Error: {e}")
        return "⚠️ عذراً، حدث خطأ في الاتصال بالذكاء الاصطناعي. حاول مرة أخرى."

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "أهلاً بك في **معلم الرياضيات الذكي**! 🧠🧮\n\n"
        "أنا الآن أستخدم الذكاء الاصطناعي لأشرح لك أي مسألة خطوة بخطوة، وأقدر أختبرك!\n\n"
        "اختر من الأزرار تحت 👇 أو اكتب مسألتك مباشرة.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.message(F.text == "ℹ️ مساعدة")
async def cmd_help(message: types.Message):
    await message.answer(
        "📖 **كيف تستخدمني؟**\n\n"
        "• **حل مسألة:** اكتب أي مسألة مثل `2x+5=15` أو `جذر 144` أو `احسب مساحة دائرة نصف قطرها 5` وسأشرح لك الحل خطوة بخطوة.\n"
        "• **اختبرني:** اضغط الزر وسأعطيك سؤالاً لتجيب عليه.\n"
        "• **سجلي:** يعرض لك آخر العمليات التي قمت بها.",
        reply_markup=keyboard,
        parse_mode="Markdown"
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

# معالجة المسائل العامة (حل المسائل)
@dp.message(F.text == "🧮 حل مسألة")
async def ask_math(message: types.Message):
    await message.answer("✍️ اكتب المسألة الآن، وسأشرح لك الحل خطوة بخطوة:")

# ميزة الاختبار
@dp.message(F.text == "📝 اختبرني")
async def test_me(message: types.Message):
    await message.answer("⏳ جاري تحضير سؤال لك...")
    
    prompt = "أنت معلم رياضيات. أعطني سؤالاً رياضياً واحداً فقط (بدون الحل) مناسباً لمستوى طالب متوسط. اجعل السؤال قصيراً ومباشراً."
    question = await ask_gemini(prompt)
    
    await message.answer(f"📝 **سؤالي لك:**\n\n{question}\n\nاكتب إجابتك الآن:")

# معالجة أي نص يكتبه المستخدم (حل المسألة أو الإجابة على الاختبار)
@dp.message(F.text)
async def handle_text(message: types.Message):
    text = message.text.strip()
    
    # تجاهل أزرار القائمة
    if text in ["🧮 حل مسألة", "📝 اختبرني", "ℹ️ مساعدة", "💾 سجلي"]:
        return

    await message.answer("⏳ جاري التفكير...")
    
    # نطلب من Gemini الحل والشرح
    prompt = f"""
    أنت معلم رياضيات ذكي ومحترف. 
    المستخدم أرسل لك هذه الرسالة: "{text}"
    
    إذا كانت مسألة رياضية: قم بحلها واشرح الخطوات بالتفصيل وبطريقة بسيطة ومفهومة باللغة العربية.
    إذا كانت إجابة على سؤال سابق: صحح الإجابة (صح أم خطأ) واشرح السبب.
    إذا كانت رسالة عادية: رد عليها بود واقترح مساعدة في الرياضيات.
    
    اجعل الرد منظماً ومقروءاً (استخدم التنسيقات والنقاط).
    """
    
    response_text = await ask_gemini(prompt)
    
    # إرسال الرد
    await message.answer(response_text, parse_mode="Markdown")
    
    # حفظ في السجل (نحفظ النص الأصلي فقط)
    await save_calculation(
        user_id=message.from_user.id,
        username=message.from_user.username or "Unknown",
        category="ai_math",
        expression=text,
        result="تم الحل بواسطة AI",
        steps=[]
    )

async def main():
    await init_db()
    print("🚀 البوت الذكي شغال...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
