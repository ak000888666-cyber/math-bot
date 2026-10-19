import asyncio
import logging
import os
import json
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from google import genai

from database import init_db, save_calculation, get_history

load_dotenv()
logging.basicConfig(level=logging.INFO)

# جلب المفاتيح
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# إعداد جوجل
client = genai.Client(api_key=GEMINI_KEY)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# حفظ آخر مسألة للمستخدم عشان الاختبارات
user_sessions = {}

# الأزرار
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🧮 حل مسألة"), KeyboardButton(text="📝 اختبرني")],
        [KeyboardButton(text="💾 سجلي"), KeyboardButton(text="ℹ️ مساعدة")]
    ],
    resize_keyboard=True
)

# دالة التحدث مع Gemini (مع محاولة ثانية لو صار ضغط)
async def ask_gemini(prompt):
    try:
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=prompt,
        )
        return response.text
    except Exception as e:
        logging.error(f"Gemini Error: {e}")
        # إذا كان الخطأ بسبب تجاوز الحد (429) ننتظر ونحاول مرة ثانية
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            logging.info("Rate limit hit, waiting 10 seconds before retry...")
            await asyncio.sleep(10)
            try:
                response = client.models.generate_content(
                    model='gemini-3.8-flash',
                    contents=prompt,
                )
                return response.text
            except Exception as e2:
                logging.error(f"Gemini Retry Error: {e2}")
                return "⚠️ عذراً، الضغط على الخدمة عالي حالياً. جرب بعد شوي."
        return "⚠️ عذراً، حدث خطأ في الاتصال بالذكاء الاصطناعي."

# أمر البدء
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    name = message.from_user.first_name or "عزيزي"
    await message.answer(
        f"أهلاً يا {name}! 🧠🧮\n\n"
        "أنا معلم الرياضيات الذكي. اختر من الأزرار تحت 👇 أو اكتب مسألتك مباشرة.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

# زر المساعدة
@dp.message(F.text == "ℹ️ مساعدة")
async def cmd_help(message: types.Message):
    name = message.from_user.first_name or "عزيزي"
    await message.answer(
        f"أهلاً يا {name}، إليك كيف أستطيع مساعدتك:\n\n"
        "• اكتب أي مسألة (حساب، جبر، تحويل أنظمة) وسأشرح لك الحل.\n"
        "• اضغط 'اختبرني' لأختبرك في آخر مسألة حللتها.\n"
        "• اضغط 'سجلي' لمشاهدة آخر عملياتك.",
        reply_markup=keyboard
    )

# زر السجل
@dp.message(F.text == "💾 سجلي")
async def cmd_history(message: types.Message):
    history = await get_history(message.from_user.id, limit=5)
    if not history:
        await message.answer("📭 سجلك فارغ حالياً. جرب حل مسألة أولاً!")
        return
    text = "📊 آخر 5 عمليات لك:\n\n"
    for item in history:
        text += f"🔹 {item['expression']} = {item['result']}\n"
    await message.answer(text, reply_markup=keyboard)

# زر حل مسألة
@dp.message(F.text == "🧮 حل مسألة")
async def ask_math(message: types.Message):
    await message.answer("✍️ اكتب المسألة الآن:")

# زر الاختبار
@dp.message(F.text == "📝 اختبرني")
async def test_me(message: types.Message):
    user_id = message.from_user.id
    name = message.from_user.first_name or "عزيزي"
    
    if user_id not in user_sessions or "last_math" not in user_sessions[user_id]:
        await message.answer(f"💡 عذراً يا {name}، يجب أن تحل مسألة أولاً حتى أتمكن من اختبارك فيها!")
        return

    await message.answer("⏳ جاري تحضير سؤال اختيارات...")
    
    last_math = user_sessions[user_id]["last_math"]
    
    prompt = f"""
    أنت معلم رياضيات. الطالب (اسمه {name}) حل هذه المسألة سابقاً: "{last_math}"
    الآن، أعطني سؤالاً مشابهاً أو يعتمد على نفس المفهوم، على شكل اختيارات (أ، ب، ج، د).
    
    يجب أن يكون الرد بصيغة JSON بالضبط كالتالي (بدون أي كلام إضافي أو علامات مارك داون):
    {{
      "question": "نص السؤال هنا",
      "options": ["خيار 1", "خيار 2", "خيار 3", "خيار 4"],
      "correct_option_id": 0
    }}
    (correct_option_id هو رقم الخيار الصحيح من 0 إلى 3)
    لا تستخدم أي رموز $ أو $$ أو LaTeX.
    """
    
    response = await ask_gemini(prompt)
    try:
        clean_json = response.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_json)
        
        inline_kb = []
        labels = ["أ", "ب", "ج", "د"]
        for i, opt in enumerate(data["options"]):
            inline_kb.append([InlineKeyboardButton(text=f"{labels[i]}) {opt}", callback_data=f"quiz_{i}_{data['correct_option_id']}")])
        
        reply_markup = InlineKeyboardMarkup(inline_keyboard=inline_kb)
        await message.answer(f"📝 سؤال لك يا {name}:\n\n{data['question']}", reply_markup=reply_markup)
        
    except Exception as e:
        logging.error(f"JSON Error: {e} | Response: {response}")
        await message.answer("⚠️ عذراً، حدث خطأ في تحضير الاختبار. تأكد من حل مسألة واضحة.")

# معالجة إجابة الاختبار
@dp.callback_query(F.data.startswith("quiz_"))
async def process_quiz_answer(callback: types.CallbackQuery):
    data = callback.data.split("_")
    selected = int(data[1])
    correct = int(data[2])
    name = callback.from_user.first_name or "عزيزي"
    
    if selected == correct:
        await callback.message.answer(f"✅ ممتاز يا {name}! إجابة صحيحة. أحسنت! 🎉")
    else:
        await callback.message.answer(f"❌ للأسف يا {name}، إجابة خاطئة. حاول مرة أخرى في المسألة القادمة!")
        
    await callback.answer()

# استقبال أي نص (لحل المسائل)
@dp.message(F.text)
async def handle_text(message: types.Message):
    text = message.text.strip()
    user_id = message.from_user.id
    name = message.from_user.first_name or "عزيزي"
    
    # تجاهل الأزرار والأوامر
    if text in ["🧮 حل مسألة", "📝 اختبرني", "ℹ️ مساعدة", "💾 سجلي"] or text.startswith("/"):
        return

    await message.answer(f"⏳ جاري التفكير يا {name}...")
    
    prompt = f"""أنت معلم رياضيات ذكي ومحترف. 
    اسم الطالب: {name}
    المستخدم أرسل لك هذه الرسالة: "{text}"
    
    إذا كانت مسألة رياضية: قم بحلها واشرح الخطوات بالتفصيل.
    إذا كانت إجابة على سؤال سابق: صحح الإجابة واشرح السبب.
    
    هام جداً: لا تستخدم أي رموز مثل $ أو $$. اكتب المعادلات كنص عادي."""
    
    response_text = await ask_gemini(prompt)
    
    # حفظ آخر مسألة في الجلسة
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    user_sessions[user_id]["last_math"] = text
    
    await message.answer(response_text)
    
    # حفظ في قاعدة البيانات
    await save_calculation(
        user_id=user_id,
        username=message.from_user.username or "Unknown",
        category="ai_math",
        expression=text,
        result="تم الحل",
        steps=[]
    )

# --- جزء Keep-Alive (لإرضاء Render) ---
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
    await start_web_server()
    print("🚀 البوت شغال الآن...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
