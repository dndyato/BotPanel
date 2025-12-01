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
ADMIN_LOGGED = set()

ASK_PASS = 1


# -----------------------------
# RANDOM KEY GENERATOR
# -----------------------------
def random_suffix(length=10):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def parse_duration(val):
    val = val.lower()
    if val.endswith("d"):
        return timedelta(days=int(val[:-1]))
    if val.endswith("h"):
        return timedelta(hours=int(val[:-1]))
    if val.endswith("m"):
        return timedelta(minutes=int(val[:-1]))
    return None


# -----------------------------
# ADMIN LOGIN
# -----------------------------
async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Enter admin password:")
    return ASK_PASS


async def admin_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == ADMIN_PASSWORD:
        ADMIN_LOGGED.add(update.message.from_user.id)
        await update.message.reply_text("✅ Logged in as Admin!")
    else:
        await update.message.reply_text("❌ Wrong password.")

    return ConversationHandler.END


def is_admin(uid):
    return uid in ADMIN_LOGGED


# -----------------------------
# ADD KEY
# -----------------------------
async def add_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    if not is_admin(uid):
        return await update.message.reply_text("❌ Admin only.")

    if len(context.args) < 3:
        return await update.message.reply_text(
            "Usage:\n/addkey KEY MAX_DEVICES YYYY-MM-DD"
        )

    key = context.args[0]
    max_devices = int(context.args[1])
    expires = context.args[2]

    payload = {
        "key": key,
        "max_devices": max_devices,
        "expires": expires
    }

    r = requests.post(API_URL + "/add-key", json=payload)

    await update.message.reply_text(
        f"🔑 **Key Added Successfully!**\n"
        f"• Key: `{key}`\n"
        f"• Max Devices: `{max_devices}`\n"
        f"• Expires: `{expires}`\n\n"
        f"🌐 Site: {API_URL}",
        parse_mode="Markdown"
    )


# -----------------------------
# DELETE KEY
# -----------------------------
async def delete_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    if not is_admin(uid):
        return await update.message.reply_text("❌ Admin only.")

    if len(context.args) < 1:
        return await update.message.reply_text("Usage: /delkey KEY")

    key = context.args[0]

    r = requests.post(API_URL + "/delete-key", json={"key": key})

    await update.message.reply_text(
        f"🗑 Key Deleted:\n`{key}`",
        parse_mode="Markdown"
    )


# -----------------------------
# CHECK KEY
# -----------------------------
async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        return await update.message.reply_text("Usage: /check KEY")

    key = context.args[0]

    r = requests.post(API_URL + "/check-key", json={"key": key, "device_id": ""})
    res = r.json()

    if res.get("valid"):
        await update.message.reply_text("✅ Key is VALID!")
    else:
        await update.message.reply_text(f"❌ Invalid key.\nReason: {res.get('error')}")


# -----------------------------
# GENKEY — YOUR SPECIAL COMMAND
# -----------------------------
async def genkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    if not is_admin(uid):
        return await update.message.reply_text("❌ Admin only.")

    if len(context.args) < 3:
        return await update.message.reply_text(
            "Usage:\n"
            "`/genkey AMOUNT DURATION MAX_DEVICES`\n\n"
            "Examples:\n"
            "`/genkey 5 1d 1`\n"
            "`/genkey 10 30m 2`",
            parse_mode="Markdown"
        )

    amount = int(context.args[0])
    duration_str = context.args[1]
    max_devices = int(context.args[2])

    delta = parse_duration(duration_str)
    if not delta:
        return await update.message.reply_text("❌ Invalid duration. Use 1d / 2h / 30m.")

    expiry = (datetime.now() + delta).strftime("%Y-%m-%d %H:%M:%S")

    keys_created = []

    for _ in range(amount):
        suffix = random_suffix()
        key = f"Yato-{suffix}"
        keys_created.append(key)

        requests.post(API_URL + "/add-key", json={
            "key": key,
            "max_devices": max_devices,
            "expires": expiry
        })

    formatted = "\n".join(f"`{k}`" for k in keys_created)

    await update.message.reply_text(
        f"🎉 **Generated {amount} Keys!**\n\n"
        f"{formatted}\n\n"
        f"⏳ Duration: `{duration_str}`\n"
        f"📅 Expires: `{expiry}`\n"
        f"📦 Max Devices: `{max_devices}`\n\n"
        f"🌐 Site: {API_URL}",
        parse_mode="Markdown"
    )


# -----------------------------
# STATS
# -----------------------------
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    if not is_admin(uid):
        return await update.message.reply_text("❌ Admin only.")

    r = requests.get(API_URL + "/get-keys")
    keys = r.json()

    now = time.time()
    total = len(keys)
    active = 0
    expired = 0

    for k in keys:
        exp_str = k["expires"]

        try:
            if len(exp_str) == 10:
                exp_ts = time.mktime(time.strptime(exp_str, "%Y-%m-%d"))
            else:
                exp_ts = time.mktime(time.strptime(exp_str, "%Y-%m-%d %H:%M:%S"))

            if exp_ts < now:
                expired += 1
            else:
                active += 1
        except:
            expired += 1

    await update.message.reply_text(
        f"📊 **Key Stats**\n"
        f"Total: {total}\n"
        f"Active: {active}\n"
        f"Expired: {expired}",
        parse_mode="Markdown"
    )


# -----------------------------
# START CMD
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Commands:\n"
        "/check KEY – Check key\n"
        "/admin – Admin login\n\n"
        "Admin Commands:\n"
        "/addkey KEY MAX_DEVICES YYYY-MM-DD\n"
        "/delkey KEY\n"
        "/genkey AMOUNT DURATION MAX_DEVICES\n"
        "/stats"
    )


# -----------------------------
# MAIN
# -----------------------------
def main():
    TOKEN = "8316549162:AAG3O0KBhuSjFjmuZ0UEedtp_UwPA7J9wMs"

    app = ApplicationBuilder().token(TOKEN).build()

    admin_handler = ConversationHandler(
        entry_points=[CommandHandler("admin", admin_cmd)],
        states={ASK_PASS: [MessageHandler(filters.TEXT, admin_pass)]},
        fallbacks=[],
    )

    app.add_handler(admin_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("check", check))
    app.add_handler(CommandHandler("addkey", add_key))
    app.add_handler(CommandHandler("delkey", delete_key))
    app.add_handler(CommandHandler("genkey", genkey))
    app.add_handler(CommandHandler("stats", stats))

    print("🤖 Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
