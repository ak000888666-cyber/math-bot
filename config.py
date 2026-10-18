import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ خطأ: التوكن BOT_TOKEN غير موجود في الإعدادات.")
