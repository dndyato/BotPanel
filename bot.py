import requests
import time
import random
import string
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------
API_URL = "https://egoistyato.pythonanywhere.com"
ADMIN_PASSWORD = "yato123"

ADMIN_LOGGED_IN = set()
ASK_PASS = 1

# ---------------------------------------------------
# ADMIN LOGIN
# ---------------------------------------------------
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔐 **Admin Login Required**\n"
        "Please enter your password:",
        parse_mode="Markdown"
    )
    return ASK_PASS

async def admin_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == ADMIN_PASSWORD:
        ADMIN_LOGGED_IN.add(update.message.from_user.id)
        await update.message.reply_text(
            "✅ **Access Granted**\n"
            "Welcome, Admin!",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "❌ **Access Denied**\n"
            "Incorrect password.",
            parse_mode="Markdown"
        )
    return ConversationHandler.END

def check_admin(uid):
    return uid in ADMIN_LOGGED_IN

# ---------------------------------------------------
# ADD KEY
# ---------------------------------------------------
async def add_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    if not check_admin(uid):
        return await update.message.reply_text("❌ Admin only.")

    if len(context.args) < 3:
        return await update.message.reply_text(
            "📘 **Usage:**\n"
            "`/addkey KEY MAX_DEVICES YYYY-MM-DD`",
            parse_mode="Markdown"
        )

    key = context.args[0]
    max_devices = int(context.args[1])
    expires = context.args[2]

    r = requests.post(API_URL + "/add-key", json={
        "key": key,
        "max_devices": max_devices,
        "expires": expires
    })

    await update.message.reply_text(
        f"✨ **Key Added Successfully!**\n"
        f"────────────────────────\n"
        f"🔑 **Key:** `{key}`\n"
        f"📦 **Max Devices:** `{max_devices}`\n"
        f"📅 **Expires:** `{expires}`\n"
        f"────────────────────────\n"
        f"🌐 **Site:** https://egoistyato.pythonanywhere.com",
        parse_mode="Markdown"
    )

# ---------------------------------------------------
# DELETE KEY
# ---------------------------------------------------
async def delete_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    if not check_admin(uid):
        return await update.message.reply_text("❌ Admin only.")

    if len(context.args) < 1:
        return await update.message.reply_text(
            "📘 **Usage:** `/delkey KEY`",
            parse_mode="Markdown"
        )

    key = context.args[0]
    requests.post(API_URL + "/delete-key", json={"key": key})

    await update.message.reply_text(
        f"🗑️ **Key Deleted Successfully**\n"
        f"────────────────────────\n"
        f"🔑 `{key}` removed.\n",
        parse_mode="Markdown"
    )

# ---------------------------------------------------
# CHECK KEY
# ---------------------------------------------------
async def check_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        return await update.message.reply_text(
            "📘 Usage: `/check KEY`",
            parse_mode="Markdown"
        )

    key = context.args[0]

    r = requests.post(API_URL + "/check-key", json={"key": key, "device_id": ""})
    res = r.json()

    if res.get("valid"):
        await update.message.reply_text(
            "✅ **Key Status: VALID**\n"
            "This key is active and working.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"❌ **Key Status: INVALID**\n"
            f"Reason: `{res.get('error')}`",
            parse_mode="Markdown"
        )

# ---------------------------------------------------
# STATS
# ---------------------------------------------------
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    if not check_admin(uid):
        return await update.message.reply_text("❌ Admin only.")

    r = requests.get(API_URL + "/get-keys")
    keys = r.json()

    total = len(keys)
    active = 0
    expired = 0

    now = datetime.now()

    for k in keys:
        exp = k["expires"]
        try:
            exp_date = datetime.strptime(exp, "%Y-%m-%d")
        except:
            exp_date = datetime.strptime(exp, "%Y-%m-%d %H:%M:%S")

        if exp_date < now:
            expired += 1
        else:
            active += 1

    await update.message.reply_text(
        "📊 **Yato Panel — Key Statistics**\n"
        "────────────────────────\n"
        f"🔢 **Total Keys:** `{total}`\n"
        f"🟢 **Active:** `{active}`\n"
        f"🔴 **Expired:** `{expired}`\n"
        "────────────────────────\n"
        "🌐 https://egoistyato.pythonanywhere.com",
        parse_mode="Markdown"
    )

# ---------------------------------------------------
# GENKEY
# ---------------------------------------------------
def random_suffix(length=12):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def parse_duration(text):
    text = text.lower()
    if text.endswith("d"):
        return timedelta(days=int(text[:-1]))
    if text.endswith("h"):
        return timedelta(hours=int(text[:-1]))
    if text.endswith("m"):
        return timedelta(minutes=int(text[:-1]))
    return None

async def genkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    if not check_admin(uid):
        return await update.message.reply_text("❌ Admin only.")

    if len(context.args) < 3:
        return await update.message.reply_text(
            "📘 **Usage:**\n"
            "`/genkey AMOUNT DURATION MAX_DEVICES`\n\n"
            "Example:\n"
            "`/genkey 5 1d 1`",
            parse_mode="Markdown"
        )

    amount = int(context.args[0])
    duration = parse_duration(context.args[1])
    max_devices = int(context.args[2])

    if not duration:
        return await update.message.reply_text("❌ Invalid duration. Use 1d, 2h, 30m")

    expiry = datetime.now() + duration
    expiry_text = expiry.strftime("%Y-%m-%d %H:%M:%S")

    generated = []

    for _ in range(amount):
        key = "Yato-" + random_suffix()
        generated.append(key)

        requests.post(API_URL + "/api/bot/add_key", json={
            "password": ADMIN_PASSWORD,
            "key": key,
            "max_devices": max_devices,
            "expires": expiry_text
        })

    formatted_keys = "\n".join(f"`{k}`" for k in generated)

    await update.message.reply_text(
        f"🎉 **Successfully Generated {amount} Keys!**\n"
        f"────────────────────────\n"
        f"{formatted_keys}\n\n"
        f"⏳ **Duration:** `{context.args[1]}`\n"
        f"📅 **Expires:** `{expiry_text}`\n"
        f"📦 **Max Devices:** `{max_devices}`\n"
        f"────────────────────────\n"
        f"🌐 **Site:** https://egoistyato.pythonanywhere.com",
        parse_mode="Markdown"
    )

# ---------------------------------------------------
# START
# ---------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✨ **Welcome to Yato Bot!**\n"
        "Here are your available commands:\n\n"
        "🔍 `/check KEY`\n"
        "🔐 `/admin`\n\n"
        "**Admin Commands:**\n"
        "➕ `/addkey KEY MAX_DEVICES YYYY-MM-DD`\n"
        "➖ `/delkey KEY`\n"
        "📊 `/stats`\n"
        "⚙️ `/genkey AMOUNT DURATION MAX_DEVICES`\n",
        parse_mode="Markdown"
    )

# ---------------------------------------------------
# MAIN
# ---------------------------------------------------
def main():
    TOKEN = "8316549162:AAG3O0KBhuSjFjmuZ0UEedtp_UwPA7J9wMs"
    app = ApplicationBuilder().token(TOKEN).build()

    admin_conv = ConversationHandler(
        entry_points=[CommandHandler("admin", admin_panel)],
        states={ASK_PASS: [MessageHandler(filters.TEXT, admin_password)]},
        fallbacks=[]
    )

    app.add_handler(admin_conv)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("check", check_key))
    app.add_handler(CommandHandler("addkey", add_key))
    app.add_handler(CommandHandler("delkey", delete_key))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("genkey", genkey))

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
