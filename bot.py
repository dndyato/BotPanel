import requests
import time
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters
)

# -----------------------------
# CONFIG
# -----------------------------
API_URL = "https://egoistyato.pythonanywhere.com"  # YOUR SERVER
ADMIN_PASSWORD = "yato123"
BOT_TOKEN = "8316549162:AAG3O0KBhuSjFjmuZ0UEedtp_UwPA7J9wMs"

ADMIN_LOGGED_IN = set()
ASK_PASS = 1


# -----------------------------
# ADMIN LOGIN
# -----------------------------
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Enter admin password:")
    return ASK_PASS


async def admin_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == ADMIN_PASSWORD:
        ADMIN_LOGGED_IN.add(update.message.from_user.id)
        await update.message.reply_text("✅ Logged in as admin!")
    else:
        await update.message.reply_text("❌ Wrong password.")

    return ConversationHandler.END


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

    r = requests.post(f"{API_URL}/add-key", json=payload)
    await update.message.reply_text(r.text)


# -----------------------------
# DELETE KEY
# -----------------------------
async def delete_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    if not check_admin(uid):
        return await update.message.reply_text("❌ Admin only.")

    if len(context.args) < 1:
        return await update.message.reply_text("Usage: /delkey KEY")

    key = context.args[0]

    r = requests.post(f"{API_URL}/delete-key", json={"key": key})
    await update.message.reply_text(r.text)


# -----------------------------
# CHECK KEY
# -----------------------------
async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        return await update.message.reply_text("Usage: /check KEY")

    key = context.args[0]

    r = requests.post(f"{API_URL}/check-key", json={"key": key, "device_id": ""})

    if r.status_code != 200:
        return await update.message.reply_text("Server error.")

    res = r.json()

    if res.get("valid"):
        await update.message.reply_text("✅ Key is VALID!")
    else:
        await update.message.reply_text(
            f"❌ Invalid key.\nReason: {res.get('error')}"
        )


# -----------------------------
# STATS
# -----------------------------
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    if not check_admin(uid):
        return await update.message.reply_text("❌ Admin only.")

    r = requests.get(f"{API_URL}/get-keys")
    keys = r.json()

    total = len(keys)
    active = 0
    expired = 0

    for k in keys:
        exp = k["expires"]
        ts = time.mktime(time.strptime(exp, "%Y-%m-%d"))
        if ts < time.time():
            expired += 1
        else:
            active += 1

    await update.message.reply_text(
        f"📊 *Key Stats*\n"
        f"Total: {total}\n"
        f"Active: {active}\n"
        f"Expired: {expired}",
        parse_mode="Markdown"
    )


# -----------------------------
# START
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome!\n"
        "/check KEY\n"
        "/admin\n\n"
        "Admin Commands:\n"
        "/addkey KEY MAX_DEVICES YYYY-MM-DD\n"
        "/delkey KEY\n"
        "/stats"
    )


# -----------------------------
# MAIN LOOP (NO CRASH)
# -----------------------------
async def main():
    print("🚀 Bot Starting...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Conversation handler for admin login
    admin_handler = ConversationHandler(
        entry_points=[CommandHandler("admin", admin_panel)],
        states={ASK_PASS: [MessageHandler(filters.TEXT, admin_password)]},
        fallbacks=[],
    )

    app.add_handler(admin_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("check", check))
    app.add_handler(CommandHandler("addkey", add_key))
    app.add_handler(CommandHandler("delkey", delete_key))
    app.add_handler(CommandHandler("stats", stats))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    print("🤖 Bot is running...")
    await asyncio.Event().wait()  # keeps bot alive forever


if __name__ == "__main__":
    asyncio.run(main())
