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
    await update.message.reply_text("🔐 **Enter admin password:**")
    return ASK_PASS

async def admin_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == ADMIN_PASSWORD:
        ADMIN_LOGGED_IN.add(update.message.from_user.id)
        await update.message.reply_text("✅ **Admin access granted!**")
    else:
        await update.message.reply_text("❌ Wrong password.")
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
            "Usage:\n`/addkey KEY MAX_DEVICES YYYY-MM-DD`",
            parse_mode="Markdown"
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

    if r.json().get("success"):
        await update.message.reply_text(
            f"🔑 **Key Added Successfully!**\n"
            f"• Key: `{key}`\n"
            f"• Max Devices: `{max_devices}`\n"
            f"• Expires: `{expires}`\n"
            f"🌐 Site: {API_URL}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ Failed to add key.")

# ---------------------------------------------------
# DELETE KEY
# ---------------------------------------------------
async def delete_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    if not check_admin(uid):
        return await update.message.reply_text("❌ Admin only.")

    if len(context.args) < 1:
        return await update.message.reply_text("Usage: /delkey KEY")

    key = context.args[0]

    r = requests.post(API_URL + "/api/bot/delete_key", json={
        "password": ADMIN_PASSWORD,
        "key": key
    })

    if r.json().get("success"):
        await update.message.reply_text(
            f"🗑️ **Key deleted:** `{key}`",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ Unable to delete key.")

# ---------------------------------------------------
# CHECK KEY
# ---------------------------------------------------
async def check_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        return await update.message.reply_text("Usage: /check KEY")

    key = context.args[0]

    r = requests.post(API_URL + "/check-key", json={"key": key, "device_id": ""})
    res = r.json()

    if res.get("valid"):
        await update.message.reply_text("✅ **Key is VALID!**")
    else:
        await update.message.reply_text(
            f"❌ Invalid key.\nReason: `{res.get('error')}`",
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
    if r.status_code != 200:
        return await update.message.reply_text("⚠️ Cannot fetch stats.")

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
        f"📊 **Key Statistics**\n"
        f"• Total Keys: `{total}`\n"
        f"• Active Keys: `{active}`\n"
        f"• Expired Keys: `{expired}`\n\n"
        f"🌐 Site: {API_URL}",
        parse_mode="Markdown"
    )

# ---------------------------------------------------
# GENKEY
# ---------------------------------------------------
def random_suffix(length=12):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

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
            "Usage:\n`/genkey AMOUNT DURATION MAX_DEVICES`",
            parse_mode="Markdown"
        )

    amount = int(context.args[0])
    duration = parse_duration(context.args[1])
    max_devices = int(context.args[2])

    if not duration:
        return await update.message.reply_text("❌ Invalid duration (use 1d, 1h, 30m).")

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
        f"🎉 **Generated {amount} Keys!**\n"
        f"{msg}\n\n"
        f"⏳ Duration: `{context.args[1]}`\n"
        f"📅 Expires: `{expiry_text}`\n"
        f"📦 Max Devices: `{max_devices}`\n"
        f"🌐 Site: {API_URL}",
        parse_mode="Markdown"
    )

# ---------------------------------------------------
# USERINFO
# ---------------------------------------------------
async def userinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")

    if len(context.args) < 1:
        return await update.message.reply_text("Usage: /userinfo KEY")

    key = context.args[0]

    r = requests.get(API_URL + "/get-keys")
    keys = r.json()

    data = next((k for k in keys if k["key"] == key), None)
    if not data:
        return await update.message.reply_text("❌ Key not found.")

    used_list = "\n".join(f"- `{d}`" for d in data["used_devices"]) or "None"

    await update.message.reply_text(
        f"🔍 **Key Information**\n"
        f"• Key: `{data['key']}`\n"
        f"• Max Devices: `{data['max_devices']}`\n"
        f"• Used Devices: `{len(data['used_devices'])}`\n\n"
        f"{used_list}\n\n"
        f"• Expires: `{data['expires']}`",
        parse_mode="Markdown"
    )

# ---------------------------------------------------
# RESET DEVICES
# ---------------------------------------------------
async def resetdevices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")

    if len(context.args) < 1:
        return await update.message.reply_text("Usage: /resetdevices KEY")

    key = context.args[0]

    r = requests.get(API_URL + "/get-keys")
    keys = r.json()

    found = next((k for k in keys if k["key"] == key), None)
    if not found:
        return await update.message.reply_text("❌ Key not found.")

    found["used_devices"] = []

    requests.post(API_URL + "/api/bot/add_key", json={
        "password": ADMIN_PASSWORD,
        "key": found["key"],
        "max_devices": found["max_devices"],
        "expires": found["expires"]
    })

    await update.message.reply_text(
        f"♻️ Devices reset for key `{key}`",
        parse_mode="Markdown"
    )

# ---------------------------------------------------
# EXTEND KEY
# ---------------------------------------------------
async def extend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")

    if len(context.args) < 2:
        return await update.message.reply_text("Usage: /extend KEY 1d/1h/30m")

    key = context.args[0]
    duration = parse_duration(context.args[1])

    if not duration:
        return await update.message.reply_text("❌ Invalid duration.")

    r = requests.get(API_URL + "/get-keys")
    keys = r.json()

    found = next((k for k in keys if k["key"] == key), None)
    if not found:
        return await update.message.reply_text("❌ Key not found.")

    try:
        exp = datetime.strptime(found["expires"], "%Y-%m-%d")
    except:
        exp = datetime.strptime(found["expires"], "%Y-%m-%d %H:%M:%S")

    new_expiry = exp + duration
    new_expiry_text = new_expiry.strftime("%Y-%m-%d %H:%M:%S")

    found["expires"] = new_expiry_text

    requests.post(API_URL + "/api/bot/add_key", json={
        "password": ADMIN_PASSWORD,
        "key": found["key"],
        "max_devices": found["max_devices"],
        "expires": new_expiry_text
    })

    await update.message.reply_text(
        f"⏳ **Key Extended!**\n"
        f"• Key: `{key}`\n"
        f"• New Expiry: `{new_expiry_text}`",
        parse_mode="Markdown"
    )

# ---------------------------------------------------
# START
# ---------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 **Yato Panel Bot**\n\n"
        "**User Commands:**\n"
        "/check KEY\n\n"
        "**Admin Commands:**\n"
        "/admin\n"
        "/addkey\n"
        "/delkey\n"
        "/stats\n"
        "/genkey\n"
        "/userinfo\n"
        "/resetdevices\n"
        "/extend"
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
    app.add_handler(CommandHandler("userinfo", userinfo))
    app.add_handler(CommandHandler("resetdevices", resetdevices))
    app.add_handler(CommandHandler("extend", extend))

    print("🤖 Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
