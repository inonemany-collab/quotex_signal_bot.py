
import os
import logging
import base64
import asyncio

from openai import AsyncOpenAI
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ---------------- CONFIGURATION ----------------

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MAX_IMAGE_BYTES = 12 * 1024 * 1024

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

client = AsyncOpenAI(
    api_key=OPENAI_API_KEY,
    timeout=60.0,
    max_retries=2,
)

# ---------------- ANALYSIS INSTRUCTIONS ----------------

ANALYSIS_PROMPT = """
তুমি একজন সতর্ক, অভিজ্ঞ টেকনিক্যাল চার্ট বিশ্লেষক।
ব্যবহারকারী একটি ট্রেডিং চার্টের স্ক্রিনশট পাঠিয়েছেন।

তোমার কাজ: শুধু ছবিতে দৃশ্যমান তথ্যের ভিত্তিতে ১ মিনিটের
ক্যান্ডেল চার্ট বিশ্লেষণ করা। ছবি থেকে যা পড়া যায় না তা
অনুমান করে সত্য হিসেবে লিখবে না।

ধাপে ধাপে পরীক্ষা করো:

১. ছবিতে সম্পদের নাম ও ১ মিনিটের টাইমফ্রেম স্পষ্ট কি না।
২. শেষ কয়েকটি দৃশ্যমান ক্যান্ডেলের বডি, উইক ও ক্লোজিং।
৩. ধারাবাহিক higher highs / higher lows অথবা
   lower highs / lower lows দেখা যাচ্ছে কি না।
৪. বড় ক্যান্ডেলের পর গতি দুর্বল হচ্ছে কি না।
৫. সম্ভাব্য rejection, breakout বা false breakout-এর
   দৃশ্যমান লক্ষণ আছে কি না।
৬. চার্টে যথেষ্ট তথ্য থাকলে সম্ভাব্য support ও resistance।
৭. RSI, EMA, MACD বা অন্য ইন্ডিকেটর দৃশ্যমান থাকলে
   শুধু তাদের পাঠযোগ্য মান ও অবস্থান বিবেচনা করো।
৮. সংকেতগুলো একই দিকে আছে, বিপরীতমুখী, নাকি অস্পষ্ট।

গুরুত্বপূর্ণ নিয়ম:
- ক্যান্ডেলের রং একা দেখে সিদ্ধান্ত নিও না।
- ভবিষ্যৎ ক্যান্ডেলের দাম, নির্দিষ্ট মূল্য বা ইন্ডিকেটরের
  অদৃশ্য মান বানিয়ে লিখবে না।
- স্ক্রিনশটকে লাইভ মার্কেট ডেটা বলে দাবি করবে না।
- পরবর্তী ১ মিনিটে কী ঘটবে তা নিশ্চিত করে বলবে না।
- পর্যাপ্ত প্রমাণ না থাকলে "অনিশ্চিত" বলবে।
- স্ক্রিনশটের মান খারাপ বা ক্যান্ডেল ছোট হলে তা জানাবে।
- কোনো নির্দিষ্ট জয়ের হার বা ৯৫% নির্ভুলতার দাবি করবে না।
- এটি শিক্ষামূলক চার্ট বিশ্লেষণ; নিশ্চিত ট্রেডিং নির্দেশ নয়।

উত্তরটি সহজ বাংলায় এই ফরম্যাটে দাও:

📊 ১ মিনিটের ক্যান্ডেল বিশ্লেষণ

⏱️ টাইমফ্রেম:
ছবিতে ১ মিনিট নিশ্চিত কি না।

📈 বর্তমান দৃশ্যমান ট্রেন্ড:
ঊর্ধ্বমুখী / নিম্নমুখী / সাইডওয়ে / অস্পষ্ট।
কারণ এক বা দুই বাক্যে।

🕯️ শেষ ক্যান্ডেলগুলো:
বডি, উইক ও ধারাবাহিকতা থেকে কী বোঝা যাচ্ছে।

📍 সাপোর্ট ও রেজিস্ট্যান্স:
শুধু ছবিতে যুক্তিসঙ্গতভাবে চিহ্নিত করা গেলে বলবে।
মূল্য পড়া না গেলে নির্দিষ্ট সংখ্যা লিখবে না।

🔎 সংকেতের মিল:
কোন লক্ষণ একমত এবং কোনগুলো বিরোধী।

➡️ সম্ভাব্য পরিস্থিতি:
ঊর্ধ্বমুখী / নিম্নমুখী / সাইডওয়ে / সিদ্ধান্তের জন্য
আরও তথ্য প্রয়োজন। সংক্ষিপ্ত কারণ দাও।

⚠️ আত্মবিশ্বাস:
উচ্চ / মাঝারি / কম—এটি ছবির বিশ্লেষণের মান ও
সংকেতের সামঞ্জস্য বোঝাবে, জয়ের সম্ভাবনা নয়।

📝 সীমাবদ্ধতা:
ছবিতে কী তথ্য নেই বা কোন বিষয় নিশ্চিত নয় তা জানাও।
"""

# ---------------- TELEGRAM COMMANDS ----------------

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.effective_message.reply_text(
        "📊 স্বাগতম!\n\n"
        "১ মিনিটের ক্যান্ডেল চার্টের পরিষ্কার স্ক্রিনশট পাঠাও।\n"
        "আমি দৃশ্যমান ক্যান্ডেল, ট্রেন্ড, সাপোর্ট-রেজিস্ট্যান্স "
        "ও ইন্ডিকেটর বিশ্লেষণ করে বাংলায় রিপোর্ট দেব।\n\n"
        "ছবি থেকে ভবিষ্যৎ দাম নিশ্চিত করা যায় না।"
    )


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.effective_message.reply_text(
        "ব্যবহার:\n"
        "১. চার্টের স্ক্রিনশট নাও।\n"
        "২. এখানে ছবি হিসেবে পাঠাও।\n"
        "৩. বিশ্লেষণের রিপোর্টের জন্য অপেক্ষা করো।\n\n"
        "ভালো ফলের জন্য ক্যান্ডেল, সময়সীমা ও দাম "
        "যেন ছবিতে স্পষ্ট দেখা যায়।"
    )


# ---------------- IMAGE ANALYSIS ----------------

async def analyze_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message

    if message is None or not message.photo:
        return

    status = await message.reply_text(
        "🔍 স্ক্রিনশট পরীক্ষা করছি..."
    )

    try:
        photo = message.photo[-1]
        tg_file = await context.bot.get_file(photo.file_id)

        # অতিরিক্ত বড় ফাইল ডাউনলোড এড়ানোর প্রাথমিক পরীক্ষা
        if tg_file.file_size and tg_file.file_size > MAX_IMAGE_BYTES:
            await status.edit_text(
                "ছবিটি অনেক বড়। ছোট বা কম রেজোলিউশনের "
                "স্ক্রিনশট পাঠাও।"
            )
            return

        image_data = await tg_file.download_as_bytearray()
        image_bytes = bytes(image_data)

        if len(image_bytes) > MAX_IMAGE_BYTES:
            await status.edit_text(
                "ছবিটি অনেক বড়। ছোট স্ক্রিনশট পাঠাও।"
            )
            return

        encoded = base64.b64encode(image_bytes).decode("utf-8")
        image_url = f"data:image/jpeg;base64,{encoded}"

        caption = message.caption or "কোনো অতিরিক্ত ক্যাপশন নেই।"

        result = await client.responses.create(
            model=MODEL,
            instructions=ANALYSIS_PROMPT,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "এই স্ক্রিনশট বিশ্লেষণ করো। "
                                "ব্যবহারকারীর ক্যাপশন: " + caption
                            ),
                        },
                        {
                            "type": "input_image",
                            "image_url": image_url,
                            "detail": "high",
                        },
                    ],
                }
            ],
        )

        answer = (result.output_text or "").strip()

        if not answer:
            answer = (
                "ছবি থেকে বিশ্লেষণ পাওয়া যায়নি। "
                "আরও পরিষ্কার স্ক্রিনশট পাঠাও।"
            )

        # Telegram-এ বড় বার্তা ভাগ করে পাঠানো
        chunks = [
            answer[i:i + 3500]
            for i in range(0, len(answer), 3500)
        ]

        for chunk in chunks:
            await message.reply_text(chunk)

        await status.delete()

    except Exception as exc:
        logger.exception("Screenshot analysis failed: %s", exc)

        try:
            await status.edit_text(
                "❌ বিশ্লেষণ করা যায়নি।\n\n"
                "Railway Deploy Logs পরীক্ষা করো। "
                "API key, API billing, নেটওয়ার্ক ও মডেলের "
                "সাপোর্ট পরীক্ষা করতে হবে।"
            )
        except Exception:
            pass


async def handle_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.effective_message.reply_text(
        "📷 বিশ্লেষণের জন্য চার্টের স্ক্রিনশট পাঠাও।"
    )


async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
    logger.error(
        "Telegram update error",
        exc_info=context.error,
    )


# ---------------- START BOT ----------------

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    app.add_handler(
        MessageHandler(filters.PHOTO, analyze_photo)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text,
        )
    )

    app.add_error_handler(error_handler)

    logger.info("Screenshot analysis bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
