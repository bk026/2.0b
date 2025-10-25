import os
import time
import yt_dlp
import asyncio
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)

# ===== CONFIG =====
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
CHANNEL_USERNAME = "@learntospeake_1"


# ===== Helper: Check channel membership =====
async def is_member_of_channel(app, user_id: int) -> bool:
    try:
        member = await app.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False


# ===== /start command =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    app = context.application
    is_member = await is_member_of_channel(app, user.id)
    if not is_member:
        await update.message.reply_text(
            f"🔒 पहले हमारे चैनल {CHANNEL_USERNAME} को Join करें!\nफिर /start दबाएँ।"
        )
        return

    await update.message.reply_text(
        "👋 नमस्ते!\nमुझे YouTube लिंक भेजें — मैं आपको Download options दिखाऊँगा।"
    )


# ===== Handle YouTube link =====
async def handle_youtube_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    app = context.application
    text = update.message.text.strip()

    is_member = await is_member_of_channel(app, user.id)
    if not is_member:
        await update.message.reply_text(f"❌ पहले {CHANNEL_USERNAME} को Join करें!")
        return

    if "youtube.com" not in text and "youtu.be" not in text:
        await update.message.reply_text("कृपया एक वैध YouTube लिंक भेजें।")
        return

    context.user_data["yt_link"] = text

    keyboard = [
        [InlineKeyboardButton("🎵 MP3", callback_data="mp3")],
        [
            InlineKeyboardButton("144p", callback_data="video_144"),
            InlineKeyboardButton("360p", callback_data="video_360"),
            InlineKeyboardButton("720p", callback_data="video_720"),
            InlineKeyboardButton("1080p", callback_data="video_1080"),
        ],
    ]
    await update.message.reply_text(
        "📥 Select format:", reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ===== Handle button press =====
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data
    link = context.user_data.get("yt_link")

    if not link:
        await query.edit_message_text("❌ Error: YouTube लिंक नहीं मिला।")
        return

    await query.edit_message_text("⏳ Processing... कृपया प्रतीक्षा करें।")

    mode, res = ("mp3", "360")
    if choice.startswith("video"):
        mode = "video"
        res = choice.split("_")[1]

    filename = "yt_download"
    outtmpl = f"{filename}.%(ext)s"

    try:
        if mode == "mp3":
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": outtmpl,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
                "quiet": True,
            }
        else:
            ydl_opts = {
                "format": f"bestvideo[height<={res}]+bestaudio/best",
                "merge_output_format": "mp4",
                "outtmpl": outtmpl,
                "quiet": True,
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([link])

        output_file = next((f"{filename}.{ext}" for ext in ["mp3", "mp4", "mkv", "webm"] if os.path.exists(f"{filename}.{ext}")), None)

        if not output_file:
            await query.edit_message_text("⚠️ फ़ाइल डाउनलोड नहीं हो पाई।")
            return

        size_mb = os.path.getsize(output_file) / (1024 * 1024)
        if size_mb > 50:
            await query.edit_message_text(f"⚠️ फ़ाइल {int(size_mb)}MB की है — Telegram पर नहीं भेजी जा सकती। कम क्वालिटी ट्राई करें।")
        else:
            if mode == "mp3":
                await query.message.reply_audio(audio=open(output_file, "rb"), caption="🎵 आपका MP3 तैयार है!")
            else:
                await query.message.reply_video(video=open(output_file, "rb"), caption=f"🎬 आपका Video {res}p तैयार है!")

        os.remove(output_file)

    except Exception as e:
        await query.edit_message_text(f"❌ Error: {str(e)}")


# ===== Core bot run function =====
async def run_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_youtube_link))
    app.add_handler(CallbackQueryHandler(button_callback))
    print("🤖 Bot running with auto-restart enabled...")
    await app.run_polling()


# ===== Auto-restart wrapper =====
def main():
    while True:
        try:
            asyncio.run(run_bot())
        except Exception as e:
            print(f"⚠️ Bot crashed: {e}")
            print("🔁 Restarting in 10 seconds...")
            time.sleep(10)


if __name__ == "__main__":
    main()
