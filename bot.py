import os
import time
import math
import asyncio
import nest_asyncio
import pyrogram.errors
from yt_dlp import YoutubeDL
from flask import Flask
from threading import Thread

# --- MAGIC FIX (Version Conflict Fix) ---
if not hasattr(pyrogram.errors, "GroupCallForbidden"):
    class GroupCallForbidden(Exception):
        pass
    pyrogram.errors.GroupCallForbidden = GroupCallForbidden
if not hasattr(pyrogram.errors, "GroupcallForbidden"):
    pyrogram.errors.GroupcallForbidden = pyrogram.errors.GroupCallForbidden
# --- FIX END ---

from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream, AudioQuality, VideoQuality

nest_asyncio.apply()

# ==========================================
# 👇 FLASK SERVER (RENDER LIVE RAKHNE KE LIYE) 👇
# ==========================================

app = Flask('')

@app.route('/')
def home():
    return "Bot is Running Securely! 24/7"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

def keep_alive():
    t = Thread(target=run)
    t.start()

# ==========================================
# 👇 CONFIGURATION (AB VARIABLES SE AAYEGA) 👇
# ==========================================

# Code ab Render ki settings se ye values uthayega
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OWNER_ID = int(os.environ.get("OWNER_ID"))
STRING_SESSION = os.environ.get("STRING_SESSION")

# ==========================================

# --- HELPERS ---
def humanbytes(size):
    if not size: return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'

async def progress_bar(current, total, status_msg, start_time):
    now = time.time()
    diff = now - start_time
    if round(diff % 5.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff if diff > 0 else 0
        try:
            await status_msg.edit_text(
                f"📥 **Downloading Movie...**\n"
                f"📊 {round(percentage, 2)}%\n"
                f"💾 {humanbytes(current)} of {humanbytes(total)}\n"
                f"⚡ {humanbytes(speed)}/s"
            )
        except: pass

ydl_opts = {'format': 'best', 'quiet': True, 'geo_bypass': True, 'nocheckcertificate': True}

# --- CLIENTS ---
bot = Client("bot_client", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
assistant = Client("ass_client", api_id=API_ID, api_hash=API_HASH, session_string=STRING_SESSION)
call_py = PyTgCalls(assistant)

current_movie_path = None
is_youtube_stream = False

# --- KEYBOARD ---
def get_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏸️ Pause", callback_data="pause"),
            InlineKeyboardButton("▶️ Resume", callback_data="resume")
        ],
        [
            InlineKeyboardButton("🔇 Mute", callback_data="mute"),
            InlineKeyboardButton("⏹️ Stop", callback_data="stop")
        ]
    ])

# --- 1. DOWNLOAD HANDLER ---
@bot.on_message(filters.private & (filters.video | filters.document) & filters.user(OWNER_ID))
async def save_movie(client, message):
    global current_movie_path, is_youtube_stream
    is_youtube_stream = False
    
    if current_movie_path and os.path.exists(current_movie_path):
        try: os.remove(current_movie_path)
        except: pass
    
    status_msg = await message.reply_text("📥 **Download Started...**")
    start_time = time.time()
    try:
        file_path = await message.download(progress=progress_bar, progress_args=(status_msg, start_time))
        current_movie_path = file_path
        await status_msg.edit_text(f"✅ **Movie Saved!**\nAb Group mein `/play` likhein.")
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {e}")

# --- 2. PLAY COMMAND ---
@bot.on_message(filters.group & filters.command("play") & filters.user(OWNER_ID))
async def stream_movie(client, message):
    global current_movie_path, is_youtube_stream
    
    # A. YOUTUBE
    if len(message.command) > 1:
        link = message.text.split(maxsplit=1)[1]
        msg = await message.reply_text("🔍 **YouTube Link Process ho raha hai...**")
        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=False)
                stream_url = info['url']
                title = info.get('title', 'Unknown Video')
                
                current_movie_path = stream_url
                is_youtube_stream = True
                
                await msg.edit_text(f"🔄 **VC Join kar raha hoon...**")
                
                await call_py.play(
                    message.chat.id,
                    MediaStream(
                        stream_url,
                        audio_parameters=AudioQuality.HIGH,
                        video_parameters=VideoQuality.HD_720p
                    )
                )
                await msg.edit_text(f"📺 **Playing YouTube:** `{title}`", reply_markup=get_keyboard())
                return
        except Exception as e:
            await msg.edit_text(f"❌ Error: {e}")
            return

    # B. FILE STREAM
    if not current_movie_path:
        await message.reply_text("❌ Pehle bot ke private mein video bhejo, download hone do, phir /play likho!")
        return

    try:
        msg = await message.reply_text("🔄 **Saved Movie Play kar raha hoon (Full Screen)...**")
        
        await call_py.play(
            message.chat.id,
            MediaStream(
                current_movie_path,
                audio_parameters=AudioQuality.HIGH,
                video_parameters=VideoQuality.HD_720p
            )
        )
        await msg.edit_text("🍿 **Movie Chal Rahi Hai!**", reply_markup=get_keyboard())
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

# --- BUTTONS ---
@bot.on_callback_query()
async def cb_handler(client, query: CallbackQuery):
    global current_movie_path
    
    if query.from_user.id != OWNER_ID:
        await query.answer("❌ Sirf Owner control kar sakta hai!", show_alert=True)
        return

    chat_id = query.message.chat.id
    data = query.data
    
    try:
        if data == "pause":
            await call_py.pause_stream(chat_id)
            await query.answer("Paused")
        elif data == "resume":
            await call_py.resume_stream(chat_id)
            await query.answer("Resumed")
        elif data == "mute":
            await call_py.mute_stream(chat_id)
            await query.answer("Muted")
        elif data == "stop":
            await call_py.leave_call(chat_id)
            if not is_youtube_stream and current_movie_path and os.path.exists(current_movie_path):
                try: os.remove(current_movie_path)
                except: pass
            current_movie_path = None
            await query.message.edit_text("⏹ **Stream Band Kar Di.**")
            
    except Exception as e:
        await query.answer(f"Error: {e}", show_alert=True)

async def start_services():
    print("Web Server Starting...")
    keep_alive()
    print("Bot Starting...")
    await bot.start()
    await assistant.start()
    await call_py.start()
    print("🚀 BOT LIVE! (Render + Secure Mode)")
    await idle()
    await bot.stop()
    await assistant.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_services())
