import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from config import BOT_TOKEN
from database import init_db, save_calculation, get_history
from solver import solve_arithmetic, solve_equation, binary_to_decimal, decimal_to_binary

logging.basicConfig(level=logging.INFO)

# إعدادات Webhook
WEBHOOK_HOST = os.getenv("RENDER_EXTERNAL_URL", "https://math-bot-bjrh.onrender.com") # استخدمنا الرابط من صورتك
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# الأزرار
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🧮 حساب عادي"), KeyboardButton(text="📐 معادلة")],
        [KeyboardButton(text="💾 سجلي"), KeyboardButton(text="ℹ️ مساعدة")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "أهلاً بك في **معلم الرياضيات**! 🧮\n\n"
        "اختر من الأزرار تحت 👇 أو اكتب مسألتك مباشرة.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.message(F.text == "ℹ️ مساعدة")
async def cmd_help(message: types.Message):
    await message.answer("اكتب مسألة حسابية مثل `25 * 4 + 10` أو معادلة مثل `2x + 5 = 15` أو تحويل `bin:1010`.", reply_markup=keyboard)

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

@dp.message(F.text)
async def handle_math(message: types.Message):
    text = message.text.strip()
    
    if text in ["🧮 حساب عادي", "📐 معادلة"]:
        await message.answer("✍️ اكتب المسألة الآن:")
        return

    category = ""
    result = None
    steps = []

    if text.startswith("bin:"):
        try:
            result, steps = binary_to_decimal(text.replace("bin:", "").strip())
            category = "base_conversion"
        except:
            await message.answer("⚠️ صيغة خاطئة. اكتب مثلاً: `bin:1010`", parse_mode="Markdown")
            return
    elif text.startswith("dec:"):
        try:
            result, steps = decimal_to_binary(int(text.replace("dec:", "").strip()))
            category = "base_conversion"
        except:
            await message.answer("⚠️ صيغة خاطئة. اكتب مثلاً: `dec:10`", parse_mode="Markdown")
            return
    elif "=" in text or any(c.isalpha() for c in text):
        result, steps = solve_equation(text)
        category = "equation"
        if result is None:
            await message.answer("\n".join(steps))
            return
    else:
        result, steps = solve_arithmetic(text)
        category = "arithmetic"
        if result is None:
            await message.answer("\n".join(steps))
            return

    steps_text = "\n".join(steps)
    await message.answer(f"```text\n{steps_text}\n```", parse_mode="Markdown")

    await save_calculation(
        user_id=message.from_user.id,
        username=message.from_user.username or "Unknown",
        category=category,
        expression=text,
        result=str(result),
        steps=steps
    )

# دالة بدء التطبيق
async def on_startup(bot: Bot):
    await init_db()
    await bot.set_webhook(WEBHOOK_URL)
    logging.info(f"Webhook set to {WEBHOOK_URL}")

def main():
    app = web.Application()
    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    
    # Render بيعطينا رقم المنفذ في المتغير PORT
    port = int(os.environ.get("PORT", 8080))
    web.run_app(app, host="0.0.0.0", port=port, on_startup=lambda _: asyncio.create_task(on_startup(bot)))

if __name__ == "__main__":
    main()
