import os
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# إعداد السجلات
logging.basicConfig(level=logging.INFO)

# تحميل المتغيرات
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# إعداد البوت
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# أمر /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("أهلاً بك في بوت معلم الرياضيات! 🧮\nأنا جاهز لمساعدتك.")

# أمر /calc للتجربة
@dp.message(Command("calc"))
async def cmd_calc(message: types.Message):
    # ناخذ النص بعد الأمر
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("اكتب العملية بعد الأمر، مثلاً:\n/calc 2+3")
        return
    
    expr = args[1]
    try:
        # حساب آمن بسيط
        result = eval(expr, {"__builtins__": None}, {})
        await message.answer(f"المسألة: {expr}\nالناتج: {result}")
    except:
        await message.answer("عذراً، لم أفهم العملية. تأكد من كتابتها بشكل صحيح.")

# تشغيل البوت
async def main():
    print("البوت شغال...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
