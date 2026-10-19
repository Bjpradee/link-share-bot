import os
import time
import uuid
import threading
from flask import Flask
import telebot
from pymongo import MongoClient

# --- Environment Variables ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
MONGO_URI = os.environ.get("MONGO_URI", "YOUR_MONGODB_CONNECTION_STRING")

bot = telebot.TeleBot(BOT_TOKEN)

# --- MongoDB Setup ---
client = MongoClient(MONGO_URI)
db = client["maapla_bot_db"]
links_col = db["master_links"] # Channel & File links save aagura idam

# --- 24/7 Keep-Alive Web Server ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Maapla Bot with MongoDB 24/7 Run Aaguthu!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ==========================================
# FEATURE 1: CHANNEL INVITE LINK GENERATOR
# ==========================================
@bot.message_handler(commands=['setchannel'])
def set_channel(message):
    try:
        # Usage: /setchannel -100123456789 5
        args = message.text.split()
        if len(args) != 3:
            bot.reply_to(
                message, 
                "❌ **Format Thappu Maapla!**\nIpdi kudu: `/setchannel <Channel_ID> <Minutes>`\nEx: `/setchannel -100192837465 5`", 
                parse_mode="Markdown"
            )
            return

        channel_id = args[1]
        expire_minutes = int(args[2])
        unique_code = f"ch_{str(uuid.uuid4())[:8]}"

        # MongoDB-la Save Panrom
        links_col.insert_one({
            "code": unique_code,
            "type": "channel",
            "channel_id": channel_id,
            "expire_seconds": expire_minutes * 60,
            "created_by": message.from_user.id
        })

        bot_username = bot.get_me().username
        master_link = f"https://t.me/{bot_username}?start={unique_code}"

        bot.reply_to(
            message,
            f"✅ **MongoDB-la Master Link Save Aagiruchu!**\n\n"
            f"🔗 **Users-ku Kudukka Vendiya Link:**\n{master_link}\n\n"
            f"⏳ **Time Limit:** User click panna {expire_minutes} mins-la link invalid aagidum.",
            parse_mode="Markdown"
        )
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {str(e)}")

# ==========================================
# FEATURE 2: FILE SHARING LINK GENERATOR
# ==========================================
@bot.message_handler(content_types=['document', 'video', 'audio', 'photo'])
def handle_files(message):
    try:
        file_id = None
        file_type = message.content_type

        if file_type == 'document':
            file_id = message.document.file_id
        elif file_type == 'video':
            file_id = message.video.file_id
        elif file_type == 'audio':
            file_id = message.audio.file_id
        elif file_type == 'photo':
            file_id = message.photo[-1].file_id

        unique_code = f"file_{str(uuid.uuid4())[:8]}"

        # File details-ah MongoDB-la save panrom
        links_col.insert_one({
            "code": unique_code,
            "type": "file",
            "file_id": file_id,
            "file_type": file_type,
            "caption": message.caption or ""
        })

        bot_username = bot.get_me().username
        share_link = f"https://t.me/{bot_username}?start={unique_code}"

        bot.reply_to(
            message,
            f"📁 **File Link Ready Maapla!**\n\n"
            f"🔗 **Share Link:**\n{share_link}\n\n"
            f"*Yaru intha link-ah click pannalum intha file avangaluku vandhurum.*",
            parse_mode="Markdown"
        )
    except Exception as e:
        bot.reply_to(message, f"⚠️ File save panrathula error: {str(e)}")

# ==========================================
# START COMMAND: USERS LINK CLICK PANNA WORK AAGUM IDAM
# ==========================================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    args = message.text.split()
    if len(args) > 1:
        code = args[1]
        # MongoDB-la irunthu data edukkurom
        data = links_col.find_one({"code": code})

        if not data:
            bot.reply_to(message, "❌ Intha link invalid allathu delete aagiruchu!")
            return

        # 1. Channel Link Request-ah iruntha:
        if data["type"] == "channel":
            channel_id = data["channel_id"]
            expire_sec = data["expire_seconds"]

            try:
                expire_timestamp = int(time.time()) + expire_sec
                
                # Limited Time + 1 Member Limit Invite Link
                invite = bot.create_chat_invite_link(
                    chat_id=channel_id,
                    expire_date=expire_timestamp,
                    member_limit=1
                )

                mins = expire_sec // 60
                bot.reply_to(
                    message,
                    f"🎉 **Unakkana Channel Invite Link:**\n{invite.invite_link}\n\n"
                    f"⏳ *Seekiram join panniko! Intha link innum {mins} nimishathula invalid aagidum (1 user only).*",
                    parse_mode="Markdown"
                )
            except Exception as e:
                bot.reply_to(message, "❌ Link generate panna mudiyala! Bot-ah channel-la Admin aaki 'Invite Users' permission kuduthurukingala nu check pannunga.")

        # 2. File Share Request-ah iruntha:
        elif data["type"] == "file":
            f_type = data["file_type"]
            f_id = data["file_id"]
            cap = data.get("caption", "")

            if f_type == 'document':
                bot.send_document(message.chat.id, f_id, caption=cap)
            elif f_type == 'video':
                bot.send_video(message.chat.id, f_id, caption=cap)
            elif f_type == 'audio':
                bot.send_audio(message.chat.id, f_id, caption=cap)
            elif f_type == 'photo':
                bot.send_photo(message.chat.id, f_id, caption=cap)

    else:
        bot.reply_to(
            message,
            "👋 **Vanakkam Maapla!**\n\n"
            "1️⃣ **Channel Link Create Panna:**\n`/setchannel <channel_id> <minutes>`\n\n"
            "2️⃣ **File Share Panna:**\nentha file venumnalum intha bot-ku forward pannu, udane link tharum!",
            parse_mode="Markdown"
        )

if __name__ == "__main__":
    t = threading.Thread(target=run_web)
    t.start()
    print("Bot with MongoDB Started...")
    bot.infinity_polling()
