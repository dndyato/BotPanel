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

API_URL = "https://egoistyato.pythonanywhere.com"
ADMIN_PASSWORD = "yato123"

ADMIN_LOGGED_IN = set()
ASK_PASS = 1

# -------------------- ADMIN LOGIN --------------------
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔐 Enter admin password:")
    return ASK_PASS

async def admin_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == ADMIN_PASSWORD:
        ADMIN_LOGGED_IN.add(update.message.from_user.id)
        await update.message.reply_text("✅ Admin access granted!")
    else:
        await update.message.reply_text("❌ Wrong password.")
    return ConversationHandler.END

def check_admin(uid):
    return uid in ADMIN_LOGGED_IN

# -------------------- ADD KEY --------------------
async def add_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")

    if len(context.args) < 3:
        return await update.message.reply_text("Usage:\n/addkey KEY MAX_DEVICES YYYY-MM-DD")

    key = context.args[0]
    max_devices = int(context.args[1])
    expires = context.args[2]

    r = requests.post(API_URL + "/api/bot/add_key", json={
        "password": ADMIN_PASSWORD,
        "key": key,
        "max_devices": max_devices,
        "expires": expires
    })

    res = r.json()

    if res.get("success"):
        await update.message.reply_text(
            f"🔑 Key Added\n• Key: {key}\n• Max Devices: {max_devices}\n• Expires: {expires}"
        )
    else:
        await update.message.reply_text(f"❌ Error: {res.get('error')}")

# -------------------- DELETE KEY --------------------
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

    res = r.json()

    if res.get("success"):
        await update.message.reply_text(f"🗑️ Key `{key}` deleted.")
    else:
        await update.message.reply_text(f"❌ Error: {res.get('error')}")

# -------------------- CHECK --------------------
async def check_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        return await update.message.reply_text("Usage: /check KEY")

    key = context.args[0]

    r = requests.post(API_URL + "/check-key", json={"key": key, "device_id": ""})
    res = r.json()

    if res.get("valid"):
        await update.message.reply_text("✅ Key is VALID!")
    else:
        await update.message.reply_text(f"❌ Invalid Key\nReason: {res.get('error')}")

# -------------------- CHECK INFO --------------------
async def checkinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        return await update.message.reply_text("Usage: /checkinfo KEY")

    key = context.args[0]

    r = requests.get(API_URL + f"/api/bot/keyinfo?key={key}")
    data = r.json()

    if not data.get("success"):
        return await update.message.reply_text(f"❌ Error: {data.get('error')}")

    info = data["data"]

    exp = datetime.strptime(info["expires"], "%Y-%m-%d %H:%M:%S")
    remaining = exp - datetime.now()
    days_left = remaining.days

    await update.message.reply_text(
        f"🔎 **Key Information**\n\n"
        f"🔑 Key: `{info['key']}`\n"
        f"📦 Max Devices: `{info['max_devices']}`\n"
        f"📱 Used Devices: `{len(info['devices'])}`\n"
        f"📅 Expires: `{info['expires']}`\n"
        f"⏳ Days Remaining: `{days_left}`\n"
        f"🟢 Status: {'Active' if days_left > 0 else 'Expired'}",
        parse_mode="Markdown"
    )

# -------------------- EXTEND KEY --------------------
def parse_duration(text):
    text = text.lower()
    if text.endswith("d"):
        return timedelta(days=int(text[:-1]))
    if text.endswith("h"):
        return timedelta(hours=int(text[:-1]))
    if text.endswith("m"):
        return timedelta(minutes=int(text[:-1]))
    return None

async def extend_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")

    if len(context.args) < 2:
        return await update.message.reply_text("Usage:\n/extend KEY 30d")

    key = context.args[0]
    duration = parse_duration(context.args[1])

    if not duration:
        return await update.message.reply_text("❌ Invalid duration. Use 30d, 12h, 10m, etc.")

    r = requests.get(API_URL + f"/api/bot/keyinfo?key={key}")
    data = r.json()

    if not data.get("success"):
        return await update.message.reply_text(f"❌ Error: {data.get('error')}")

    info = data["data"]
    old_exp = datetime.strptime(info["expires"], "%Y-%m-%d %H:%M:%S")

    new_exp = old_exp + duration
    new_exp_str = new_exp.strftime("%Y-%m-%d %H:%M:%S")

    requests.post(API_URL + "/api/bot/extend_key", json={
        "password": ADMIN_PASSWORD,
        "key": key,
        "new_expiry": new_exp_str
    })

    await update.message.reply_text(
        f"⏳ **Key Extended!**\n\n"
        f"🔑 Key: `{key}`\n"
        f"📅 Old Expiry: `{info['expires']}`\n"
        f"🆕 New Expiry: `{new_exp_str}`\n"
        f"➕ Extended by: `{context.args[1]}`",
        parse_mode="Markdown"
    )

# -------------------- GENKEY --------------------
def random_suffix(length=10):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

async def genkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")

    if len(context.args) < 3:
        return await update.message.reply_text("Usage:\n/genkey AMOUNT DURATION MAX_DEVICES")

    amount = int(context.args[0])
    duration = parse_duration(context.args[1])
    max_devices = int(context.args[2])

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

    keys_msg = "\n".join(f"`{k}`" for k in generated)

    await update.message.reply_text(
        f"🎉 Generated {amount} Keys!\n\n{keys_msg}\n\nExpires: {expiry_text}",
        parse_mode="Markdown"
    )

# -------------------- START --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome!\n\n"
        "**User Commands:**\n"
        "/check KEY\n"
        "/checkinfo KEY\n\n"
        "**Admin Commands:**\n"
        "/admin\n"
        "/addkey\n"
        "/delkey\n"
        "/extend KEY 30d\n"
        "/stats\n"
        "/genkey",
        parse_mode="Markdown"
    )

# -------------------- MAIN --------------------
def main():
    TOKEN = "8316549162:AAFx8JuIJLOBA3CF-8s0yqcxYWC9gxb5Q1U"
    app = ApplicationBuilder().token(TOKEN).build()

    admin_conv = ConversationHandler(
        entry_points=[CommandHandler("admin", admin_panel)],
        states={ASK_PASS: [MessageHandler(filters.TEXT, admin_password)]},
        fallbacks=[]
    )

    app.add_handler(admin_conv)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("check", check_key))
    app.add_handler(CommandHandler("checkinfo", checkinfo))
    app.add_handler(CommandHandler("addkey", add_key))
    app.add_handler(CommandHandler("delkey", delete_key))
    app.add_handler(CommandHandler("extend", extend_key))
    app.add_handler(CommandHandler("extand", extend_key))  # your spelling
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("genkey", genkey))

    print("🤖 Bot Running…")
    app.run_polling()

if __name__ == "__main__":
    main()
