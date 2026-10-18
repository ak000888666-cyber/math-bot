import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from config import BOT_TOKEN
from database import init_db, save_calculation, get_history
from solver import solve_arithmetic, solve_equation, decimal_to_binary, binary_to_decimal, decimal_to_hex, hex_to_decimal

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# أزرار الكيبورد
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🧮 حساب عادي"), KeyboardButton(text="📐 معادلة")],
        [KeyboardButton(text="🔢 ثنائي → عشري"), KeyboardButton(text="🔢 عشري → ثنائي")],
        [KeyboardButton(text="💾 سجلي"), KeyboardButton(text="ℹ️ مساعدة")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "أهلاً بك في **معلم الرياضيات**! 🧮\n\n"
        "أنا بوت ذكي أحسب، أحل المعادلات، وأحول بين أنظمة الأعداد (ثنائي، عشري، ست عشري)، **وأشرح لك الخطوات**!\n\n"
        "اختر من الأزرار تحت 👇 أو اكتب مسألتك مباشرة.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.message(F.text == "ℹ️ مساعدة")
async def cmd_help(message: types.Message):
    await message.answer(
        "📖 **كيف تستخدمني؟**\n\n"
        "• **حساب عادي:** اكتب مثلاً `25 * 4 + 10`\n"
        "• **معادلة:** اكتب مثلاً `2x + 5 = 15`\n"
        "• **تحويل:** اكتب `bin:1010` (لتحويل من ثنائي لعشري)\n\n"
        "كل عملية سأشرح لك خطوات حلها! ✨",
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

# دالة معالجة النصوص (المسائل)
@dp.message(F.text)
async def handle_math(message: types.Message):
    text = message.text.strip()
    
    # إذا كتب أزرار القائمة، نتجاهلها (لأن لها أوامر خاصة)
    if text in ["🧮 حساب عادي", "📐 معادلة", "🔢 ثنائي → عشري", "🔢 عشري → ثنائي"]:
        await message.answer("✍️ اكتب المسألة أو الرقم الآن:")
        return

    category = ""
    result = None
    steps = []

    # 1. تحويل من ثنائي إلى عشري
    if text.startswith("bin:"):
        try:
            num_str = text.replace("bin:", "").strip()
            result, steps = binary_to_decimal(num_str)
            category = "base_conversion"
        except:
            await message.answer("⚠️ صيغة خاطئة. اكتب مثلاً: `bin:1010`", parse_mode="Markdown")
            return

    # 2. تحويل من عشري إلى ثنائي
    elif text.startswith("dec:"):
        try:
            num = int(text.replace("dec:", "").strip())
            result, steps = decimal_to_binary(num)
            category = "base_conversion"
        except:
            await message.answer("⚠️ صيغة خاطئة. اكتب مثلاً: `dec:10`", parse_mode="Markdown")
            return

    # 3. معادلة (فيها = أو حرف)
    elif "=" in text or any(c.isalpha() for c in text):
        result, steps = solve_equation(text)
        category = "equation"
        if result is None:
            await message.answer("\n".join(steps))
            return

    # 4. حساب عادي
    else:
        result, steps = solve_arithmetic(text)
        category = "arithmetic"
        if result is None:
            await message.answer("\n".join(steps))
            return

    # إرسال الخطوات
    steps_text = "\n".join(steps)
    await message.answer(f"```text\n{steps_text}\n```", parse_mode="Markdown")

    # حفظ في السجل
    await save_calculation(
        user_id=message.from_user.id,
        username=message.from_user.username or "Unknown",
        category=category,
        expression=text,
        result=str(result),
        steps=steps
    )

async def main():
    await init_db()
    print("🚀 البوت شغال الآن...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
