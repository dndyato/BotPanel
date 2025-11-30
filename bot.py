import requests
import time
import json
import random
import string
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

# -----------------------------
# CONFIG
# -----------------------------
API_URL = "https://egoistyato.pythonanywhere.com"
ADMIN_PASSWORD = "yato123"

ADMIN_LOGGED_IN = set()

# -----------------------------
# ADMIN LOGIN
# -----------------------------
ASK_PASS = 1

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔐 *Enter admin password:*", parse_mode="Markdown")
    return ASK_PASS

async def admin_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == ADMIN_PASSWORD:
        ADMIN_LOGGED_IN.add(update.message.from_user.id)
        await update.message.reply_text("✅ *Logged in as admin!*", parse_mode="Markdown")
        return ConversationHandler.END
    else:
        await update.message.reply_text("❌ Wrong password.")
        return ConversationHandler.END


# -----------------------------
# CHECK ADMIN
# -----------------------------
def check_admin(uid):
    return uid in ADMIN_LOGGED_IN


# -----------------------------
# ADD KEY
# -----------------------------
async def add_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    if not check_admin(uid):
        return await update.message.reply_text("❌ Admin only.")

    if len(context.args) < 3:
        return await update.message.reply_text(
            "Usage:\n`/addkey KEY MAX_DEVICES YYYY-MM-DD`",
            parse_mode="Markdown"
        )

    key = context.args[0]
    max_devices = int(context.args[1])
    expires = context.args[2]

    payload = {
        "password": ADMIN_PASSWORD,
        "key": key,
        "max_devices": max_devices,
        "expires": expires
    }

    r = requests.post(API_URL + "/api/bot/add_key", json=payload)

    await update.message.reply_text(
        f"🔑 **Key Added Successfully!**\n"
        f"• Key: `{key}`\n"
        f"• Max Devices: `{max_devices}`\n"
        f"• Expiry: `{expires}`\n"
        f"🌐 Site: {API_URL}",
        parse_mode="Markdown"
    )


# -----------------------------
# DELETE KEY
# -----------------------------
async def delete_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    if not check_admin(uid):
        return await update.message.reply_text("❌ Admin only.")

    if len(context.args) < 1:
        return await update.message.reply_text("Usage: `/delkey KEY`", parse_mode="Markdown")

    key = context.args[0]

    r = requests.post(API_URL + "/api/bot/delete_key",
                      json={"password": ADMIN_PASSWORD, "key": key})

    await update.message.reply_text(
        f"🗑️ Key `{key}` deleted.\n"
        f"🌐 Site: {API_URL}",
        parse_mode="Markdown"
    )


# -----------------------------
# CHECK KEY
# -----------------------------
async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        return await update.message.reply_text("Usage: `/check KEY`", parse_mode="Markdown")

    key = context.args[0]

    r = requests.post(API_URL + "/check-key",
                      json={"key": key, "device_id": ""})

    if r.status_code != 200:
        return await update.message.reply_text("❌ Server error.")

    data = r.json()

    if data.get("valid"):
        await update.message.reply_text("✅ *Key is VALID!*", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ Invalid key.\nReason: {data.get('error')}")


# -----------------------------
# STATS
# -----------------------------
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    if not check_admin(uid):
        return await update.message.reply_text("❌ Admin only.")

    r = requests.get(API_URL + "/api/bot/get_keys",
                     json={"password": ADMIN_PASSWORD})

    try:
        keys = r.json()
    except:
        return await update.message.reply_text("❌ Server returned invalid data.")

    total = len(keys)
    active = 0
    expired = 0

    for k in keys:
        exp = k["expires"]
        exp_ts = time.mktime(time.strptime(exp, "%Y-%m-%d"))
        if exp_ts < time.time():
            expired += 1
        else:
            active += 1

    await update.message.reply_text(
        f"📊 *Key Stats*\n"
        f"Total: `{total}`\n"
        f"Active: `{active}`\n"
        f"Expired: `{expired}`",
        parse_mode="Markdown"
    )


# -----------------------------
# GENKEY (NEW)
# -----------------------------
def generate_key_suffix(length=12):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def parse_duration(v):
    v = v.lower()
    if v.endswith("d"):
        return timedelta(days=int(v[:-1]))
    if v.endswith("h"):
        return timedelta(hours=int(v[:-1]))
    if v.endswith("m"):
        return timedelta(minutes=int(v[:-1]))
    return None


async def genkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    if not check_admin(uid):
        return await update.message.reply_text("❌ Admin only.")

    if len(context.args) < 3:
        return await update.message.reply_text(
            "Usage:\n`/genkey AMOUNT DURATION MAX_DEVICES`\n"
            "Example:\n`/genkey 5 1d 1`",
            parse_mode="Markdown"
        )

    amount = int(context.args[0])
    duration = parse_duration(context.args[1])
    max_devices = int(context.args[2])

    if not duration:
        return await update.message.reply_text(
            "❌ Invalid duration. Use: `1d`, `12h`, `30m`, etc.",
            parse_mode="Markdown"
        )

    expire = (datetime.now() + duration).strftime("%Y-%m-%d")
    generated = []

    for _ in range(amount):
        key = "Yato-" + generate_key_suffix()
        generated.append(key)

        requests.post(API_URL + "/api/bot/add_key", json={
            "password": ADMIN_PASSWORD,
            "key": key,
            "max_devices": max_devices,
            "expires": expire
        })

    txt = "\n".join(f"`{k}`" for k in generated)

    await update.message.reply_text(
        f"🎉 **Generated {amount} Keys!**\n\n"
        f"{txt}\n\n"
        f"⏳ Duration: `{context.args[1]}`\n"
        f"📅 Expires: `{expire}`\n"
        f"📦 Max Devices: `{max_devices}`\n"
        f"🌐 Site: {API_URL}",
        parse_mode="Markdown"
    )


# -----------------------------
# START
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "**Welcome to Yato Key Bot!** 🔑\n\n"
        "User Commands:\n"
        "• `/check KEY`\n\n"
        "Admin Commands:\n"
        "• `/admin` – Login\n"
        "• `/addkey KEY MAX YYYY-MM-DD`\n"
        "• `/delkey KEY`\n"
        "• `/stats`\n"
        "• `/genkey AMOUNT DURATION MAX`\n",
        parse_mode="Markdown"
    )


# -----------------------------
# BOT MAIN
# -----------------------------
def main():
    TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"

    app = ApplicationBuilder().token(TOKEN).build()

    admin_handler = ConversationHandler(
        entry_points=[CommandHandler("admin", admin_panel)],
        states={ASK_PASS: [MessageHandler(filters.TEXT, admin_password)]},
        fallbacks=[]
    )

    app.add_handler(admin_handler)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("check", check))
    app.add_handler(CommandHandler("addkey", add_key))
    app.add_handler(CommandHandler("delkey", delete_key))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("genkey", genkey))

    print("🤖 Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
