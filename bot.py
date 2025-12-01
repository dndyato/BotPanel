import requests
import random
import string
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

API_URL = "https://egoistyato.pythonanywhere.com"
ADMIN_PASSWORD = "yato123"

ADMIN_LOGGED_IN = set()
ASK_PASS = 1

# ---------------------------------------------------
# SAFE JSON
# ---------------------------------------------------
def safe_json(r):
    try:
        return r.json()
    except:
        return {"success": False, "error": "Invalid JSON response from server"}

# ---------------------------------------------------
# ADMIN LOGIN
# ---------------------------------------------------
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔐 Enter admin password:", parse_mode="Markdown")
    return ASK_PASS

async def admin_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == ADMIN_PASSWORD:
        ADMIN_LOGGED_IN.add(update.message.from_user.id)
        await update.message.reply_text("✅ Admin access granted!", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Wrong password.")
    return ConversationHandler.END

def check_admin(uid):
    return uid in ADMIN_LOGGED_IN

# ---------------------------------------------------
# ADD KEY
# ---------------------------------------------------
async def add_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")

    if len(context.args) < 3:
        return await update.message.reply_text(
            "Usage:\n`/addkey KEY MAX_DEVICES YYYY-MM-DD`",
            parse_mode="Markdown",
        )

    key = context.args[0]
    max_devices = int(context.args[1])
    expires = context.args[2]

    r = requests.post(API_URL + "/api/bot/add_key", json={
        "password": ADMIN_PASSWORD,
        "key": key,
        "max_devices": max_devices,
        "expires": expires
    })

    res = safe_json(r)

    if res.get("success"):
        await update.message.reply_text(
            f"🔑 **Key Added Successfully!**\n\n"
            f"• Key: `{key}`\n"
            f"• Max Devices: `{max_devices}`\n"
            f"• Expires: `{expires}`\n"
            f"🌐 Site: {API_URL}",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(f"❌ Error: {res.get('error')}")

# ---------------------------------------------------
# DELETE KEY
# ---------------------------------------------------
async def delete_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")

    if len(context.args) < 1:
        return await update.message.reply_text("Usage: /delkey KEY")

    key = context.args[0]

    r = requests.post(API_URL + "/api/bot/delete_key", json={
        "password": ADMIN_PASSWORD,
        "key": key
    })

    res = safe_json(r)

    if res.get("success"):
        await update.message.reply_text(f"🗑️ Key `{key}` deleted.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ Error: {res.get('error')}")

# ---------------------------------------------------
# CHECK KEY VALIDITY
# ---------------------------------------------------
async def check_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        return await update.message.reply_text("Usage: /check KEY")

    key = context.args[0]

    r = requests.post(API_URL + "/check-key", json={"key": key, "device_id": ""})
    res = safe_json(r)

    if res.get("valid"):
        await update.message.reply_text("✅ **Key is VALID!**", parse_mode="Markdown")
    else:
        await update.message.reply_text(
            f"❌ Invalid Key\nReason: `{res.get('error')}`",
            parse_mode="Markdown"
        )

# ---------------------------------------------------
# CHECK INFO
# ---------------------------------------------------
async def check_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        return await update.message.reply_text("Usage: /checkinfo KEY")

    key = context.args[0]

    r = requests.get(API_URL + "/api/bot/checkinfo", params={"key": key})
    res = safe_json(r)

    if not res.get("success"):
        return await update.message.reply_text(f"❌ Error: `{res.get('error')}`", parse_mode="Markdown")

    await update.message.reply_text(
        "🔍 **Key Information**\n\n"
        f"🔑 Key: `{res.get('key')}`\n"
        f"📦 Max Devices: `{res.get('max_devices')}`\n"
        f"📱 Used Devices: `{res.get('used_devices')}`\n"
        f"📅 Expires: `{res.get('expires')}`",
        parse_mode="Markdown",
    )

# ---------------------------------------------------
# FIXED EXTEND KEY WITH DURATION PARSER
# ---------------------------------------------------
def parse_days(value):
    """Accepts: 1 => 1 day, '1d' => 1 day, '5d' => 5 days"""
    v = value.lower()
    if v.endswith("d"):
        return int(v[:-1])
    return int(v)

async def extend_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")

    if len(context.args) < 2:
        return await update.message.reply_text("Usage: /extend KEY DAYS")

    key = context.args[0]

    try:
        days = parse_days(context.args[1])
    except:
        return await update.message.reply_text("❌ Invalid duration. Example: 1d / 7d / 10")

    r = requests.post(API_URL + "/api/bot/extend", json={
        "password": ADMIN_PASSWORD,
        "key": key,
        "days": days
    })

    res = safe_json(r)

    if res.get("success"):
        await update.message.reply_text(
            f"⏳ **Key Extended!**\n\n"
            f"🔑 Key: `{key}`\n"
            f"➕ Days Added: `{days}`\n"
            f"📅 New Expiry: `{res.get('new_exp')}`",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(f"❌ Error: {res.get('error')}")

# ---------------------------------------------------
# STATS
# ---------------------------------------------------
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")

    r = requests.get(API_URL + "/api/bot/stats")
    res = safe_json(r)

    if not isinstance(res, list):
        return await update.message.reply_text("❌ Unexpected server response")

    now = datetime.now()
    total = len(res)
    active = 0
    expired = 0

    for k in res:
        try:
            exp = datetime.strptime(k["expires"], "%Y-%m-%d")
        except:
            exp = datetime.strptime(k["expires"], "%Y-%m-%d %H:%M:%S")

        if exp < now:
            expired += 1
        else:
            active += 1

    await update.message.reply_text(
        f"📊 **Panel Statistics**\n\n"
        f"🔑 Total Keys: **{total}**\n"
        f"🟢 Active: **{active}**\n"
        f"🔴 Expired: **{expired}**\n"
        f"🌐 Site: {API_URL}",
        parse_mode="Markdown",
    )

# ---------------------------------------------------
# GENKEY
# ---------------------------------------------------
def random_suffix(length=10):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def parse_duration(text):
    text = text.lower()
    if text.endswith("d"): return timedelta(days=int(text[:-1]))
    if text.endswith("h"): return timedelta(hours=int(text[:-1]))
    if text.endswith("m"): return timedelta(minutes=int(text[:-1]))
    return None

async def genkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")

    if len(context.args) < 3:
        return await update.message.reply_text(
            "Usage:\n`/genkey AMOUNT DURATION MAX_DEVICES`\nExample: `/genkey 5 1d 1`",
            parse_mode="Markdown",
        )

    amount = int(context.args[0])
    duration = parse_duration(context.args[1])
    max_devices = int(context.args[2])

    if not duration:
        return await update.message.reply_text("❌ Invalid duration. Use 1d, 1h, 30m")

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

    msg = "\n".join(f"`{k}`" for k in generated)
    await update.message.reply_text(
        f"🎉 **Generated {amount} Keys!**\n\n"
        f"{msg}\n\n"
        f"⏳ Duration: `{context.args[1]}`\n"
        f"📅 Expires: `{expiry_text}`\n"
        f"📦 Max Devices: `{max_devices}`\n"
        f"🌐 Site: {API_URL}",
        parse_mode="Markdown"
    )

# ---------------------------------------------------
# START MESSAGE
# ---------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 **Welcome to Yato Panel Bot!**\n\n"
        "**User Commands:**\n"
        "• `/check KEY` – Check if a key is valid\n"
        "• `/checkinfo KEY` – Detailed key info\n\n"
        "**Admin Commands:**\n"
        "• `/admin` – Login\n"
        "• `/addkey KEY MAXDEV YYYY-MM-DD`\n"
        "• `/delkey KEY`\n"
        "• `/extend KEY DAYS`\n"
        "• `/stats`\n"
        "• `/genkey AMOUNT TIME MAXDEV`",
        parse_mode="Markdown"
    )

# ---------------------------------------------------
# MAIN
# ---------------------------------------------------
def main():
    TOKEN = "8316549162:AAHAOOCTDzeAn0ClziHmc03dj3NBSNpGatA"
    app = ApplicationBuilder().token(TOKEN).build()

    admin_conv = ConversationHandler(
        entry_points=[CommandHandler("admin", admin_panel)],
        states={ASK_PASS: [MessageHandler(filters.TEXT, admin_password)]},
        fallbacks=[]
    )

    app.add_handler(admin_conv)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("check", check_key))
    app.add_handler(CommandHandler("checkinfo", check_info))
    app.add_handler(CommandHandler("extend", extend_key))
    app.add_handler(CommandHandler("addkey", add_key))
    app.add_handler(CommandHandler("delkey", delete_key))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("genkey", genkey))

    print("🤖 Bot Running…")
    app.run_polling()

if __name__ == "__main__":
    main()
