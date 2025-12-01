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
# iOS STYLE QUOTE BUBBLE
# ---------------------------------------------------
async def reply_quote(update, text):
    bubble = f"""
╭───────◦●◦────────
│  {text}
╰──────────────────
""".strip()

    await update.message.reply_text(
        bubble,
        parse_mode="Markdown",
        reply_to_message_id=update.message.message_id
    )

# ---------------------------------------------------
# ADMIN LOGIN
# ---------------------------------------------------
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await reply_quote(update, "🔐 **Enter admin password:**\n(Reply here)")

async def admin_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == ADMIN_PASSWORD:
        ADMIN_LOGGED_IN.add(update.message.from_user.id)
        return await reply_quote(update, "✅ **Admin access granted!**")
    else:
        return await reply_quote(update, "❌ Wrong password.")

def check_admin(uid):
    return uid in ADMIN_LOGGED_IN

# ---------------------------------------------------
# ADD KEY
# ---------------------------------------------------
async def add_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    if not check_admin(uid):
        return await reply_quote(update, "❌ *Admin only.*")

    if len(context.args) < 3:
        return await reply_quote(update,
            "Usage:\n`/addkey KEY MAX_DEVICES YYYY-MM-DD`"
        )

    key = context.args[0]
    max_devices = int(context.args[1])
    expires = context.args[2]

    r = requests.post(API_URL + "/admin/add-key", json={
        "key": key,
        "max_devices": max_devices,
        "expires": expires
    })

    return await reply_quote(update, f"📌 `{r.text}`")

# ---------------------------------------------------
# DELETE KEY
# ---------------------------------------------------
async def delete_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    if not check_admin(uid):
        return await reply_quote(update, "❌ *Admin only.*")

    if len(context.args) < 1:
        return await reply_quote(update, "Usage: `/delkey KEY`")

    key = context.args[0]

    r = requests.post(API_URL + "/admin/delete-key", json={"key": key})
    return await reply_quote(update, f"🗑 `{r.text}`")

# ---------------------------------------------------
# CHECK KEY
# ---------------------------------------------------
async def check_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        return await reply_quote(update, "Usage: `/check KEY`")

    key = context.args[0]

    r = requests.post(API_URL + "/check-key", json={"key": key, "device_id": ""})
    res = r.json()

    if res.get("valid"):
        await reply_quote(update, "✅ **Key is VALID!**")
    else:
        await reply_quote(update, f"❌ Invalid key.\nReason: *{res.get('error')}*")

# ---------------------------------------------------
# STATS
# ---------------------------------------------------
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    if not check_admin(uid):
        return await reply_quote(update, "❌ *Admin only.*")

    r = requests.get(API_URL + "/admin/get-keys")
    if r.status_code != 200:
        return await reply_quote(update, "⚠️ Server error while fetching stats.")

    keys = r.json()
    total = len(keys)
    active, expired = 0, 0
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

    msg = (
        f"📊 **Panel Statistics**\n\n"
        f"🔑 Total Keys: `{total}`\n"
        f"🟢 Active: `{active}`\n"
        f"🔴 Expired: `{expired}`\n"
        f"🌐 Site: https://egoistyato.pythonanywhere.com"
    )

    return await reply_quote(update, msg)

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
        return await reply_quote(update, "❌ *Admin only.*")

    if len(context.args) < 3:
        return await reply_quote(update,
            "Usage:\n`/genkey AMOUNT DURATION MAX_DEVICES`\n"
            "Example: `/genkey 5 1d 1`"
        )

    amount = int(context.args[0])
    duration = parse_duration(context.args[1])
    max_devices = int(context.args[2])

    if not duration:
        return await reply_quote(update, "❌ Invalid duration. Use: 1d, 2h, 30m")

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

    msg = (
        f"🎉 **Generated {amount} Keys!**\n\n" +
        "\n".join(f"`{k}`" for k in generated) +
        f"\n\n⏳ Duration: `{context.args[1]}`"
        f"\n📅 Expires: `{expiry_text}`"
        f"\n📦 Max Devices: `{max_devices}`"
        f"\n🌐 Site: https://egoistyato.pythonanywhere.com"
    )

    return await reply_quote(update, msg)

# ---------------------------------------------------
# START
# ---------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply_quote(update,
        "👋 **Welcome to the Yato Key Panel Bot!**\n\n"
        "**User Commands:**\n"
        "• `/check KEY`\n\n"
        "**Admin Commands:**\n"
        "• `/admin`\n"
        "• `/addkey KEY MAX_DEVICES YYYY-MM-DD`\n"
        "• `/delkey KEY`\n"
        "• `/stats`\n"
        "• `/genkey AMOUNT DURATION MAX_DEVICES`\n"
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
