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

BOT_TOKEN = os.getenv("BOT_TOKEN")

# --- نظام تبديل المفاتيح التلقائي ---
# نضع المفاتيح في قائمة. تأكد من إضافتها في Render كمتغيرات بيئة
# GEMINI_API_KEY_1, GEMINI_API_KEY_2, GEMINI_API_KEY_3 ... إلخ
raw_keys = []
for i in range(1, 6): # يدعم حتى 5 مفاتيح
    key = os.getenv(f"GEMINI_API_KEY_{i}")
    if key:
        raw_keys.append(key)

if not raw_keys:
    # في حال وجود مفتاح واحد فقط بالاسم القديم
    old_key = os.getenv("GEMINI_API_KEY")
    if old_key:
        raw_keys.append(old_key)
    else:
        raise ValueError("لا يوجد أي مفتاح Gemini في متغيرات البيئة!")

current_key_index = 0
client = genai.Client(api_key=raw_keys[current_key_index])
# ------------------------------------

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

user_sessions = {}
user_locks = {} 

keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🧮 حل مسألة"), KeyboardButton(text="📝 اختبرني")],
        [KeyboardButton(text="💾 سجلي"), KeyboardButton(text="ℹ️ مساعدة")]
    ],
    resize_keyboard=True
)

# دالة التحدث مع Gemini مع تبديل المفاتيح
async def ask_gemini(prompt):
    global current_key_index, client
    
    max_attempts = len(raw_keys) * 2 # نحاول مع كل مفتاح مرتين
    attempts = 0
    
    while attempts < max_attempts:
        try:
            response = client.models.generate_content(
                model='gemini-3.8-flash',
                contents=prompt,
            )
            return response.text
        except Exception as e:
            error_str = str(e)
            logging.error(f"Gemini Error with key index {current_key_index}: {error_str}")
            
            # إذا كان الخطأ هو تجاوز الحد (429) أو نفاد الموارد
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                current_key_index = (current_key_index + 1) % len(raw_keys) # التبديل للمفتاح التالي
                logging.info(f"Switching to API Key Index: {current_key_index}")
                client = genai.Client(api_key=raw_keys[current_key_index])
                attempts += 1
                await asyncio.sleep(2) # انتظار بسيط قبل المحاولة بالمفتاح الجديد
            else:
                # إذا كان خطأ آخر، لا داعي للتبديل
                return "⚠️ عذراً، حدث خطأ في الاتصال بالذكاء الاصطناعي."
                
    return "⚠️ عذراً، جميع المفاتيح وصلت للحد الأقصى. جرب بعد شوي."

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    name = message.from_user.first_name or "عزيزي"
    await message.answer(
        f"أهلاً يا {name}! 🧠🧮\n\n"
        "أنا معلم الرياضيات الذكي. اختر من الأزرار تحت 👇 أو اكتب مسألتك مباشرة.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

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

@dp.message(F.text == "🧮 حل مسألة")
async def ask_math(message: types.Message):
    await message.answer("✍️ اكتب المسألة الآن:")

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

@dp.message(F.text)
async def handle_text(message: types.Message):
    text = message.text.strip()
    user_id = message.from_user.id
    name = message.from_user.first_name or "عزيزي"
    
    if text in ["🧮 حل مسألة", "📝 اختبرني", "ℹ️ مساعدة", "💾 سجلي"] or text.startswith("/"):
        return

    # 🛑 القفل: إذا كان المستخدم يرسل طلب، نتجاهل الطلب الجديد
    if user_id in user_locks and user_locks[user_id]:
        return 
    user_locks[user_id] = True

    await message.answer(f"⏳ جاري التفكير يا {name}...")
    
    prompt = f"""أنت معلم رياضيات ذكي ومحترف. 
    اسم الطالب: {name}
    المستخدم أرسل لك هذه الرسالة: "{text}"
    
    إذا كانت مسألة رياضية: قم بحلها واشرح الخطوات بالتفصيل.
    إذا كانت إجابة على سؤال سابق: صحح الإجابة واشرح السبب.
    
    هام جداً: لا تستخدم أي رموز مثل $ أو $$. اكتب المعادلات كنص عادي."""
    
    response_text = await ask_gemini(prompt)
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    user_sessions[user_id]["last_math"] = text
    
    await message.answer(response_text)
    
    await save_calculation(
        user_id=user_id,
        username=message.from_user.username or "Unknown",
        category="ai_math",
        expression=text,
        result="تم الحل",
        steps=[]
    )

    # 🔓 فتح القفل بعد الانتهاء
    user_locks[user_id] = False

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
    print(f"🚀 البوت شغال الآن... ({len(raw_keys)} مفاتيح جاهزة)")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
