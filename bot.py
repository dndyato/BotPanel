import requests
import time
from datetime import datetime
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


def check_admin(user_id):
    return user_id in ADMIN_LOGGED_IN


# -----------------------------
# ADD KEY
# -----------------------------
async def add_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")

    if len(context.args) < 3:
        return await update.message.reply_text("Usage: /addkey KEY MAX_DEVICES YYYY-MM-DD")

    key = context.args[0]
    max_devices = context.args[1]
    expires = context.args[2]

    r = requests.post(API_URL + "/api/bot/add_key", json={
        "password": ADMIN_PASSWORD,
        "key": key,
        "max_devices": max_devices,
        "expires": expires
    })

    await update.message.reply_text(r.text)


# -----------------------------
# DELETE KEY
# -----------------------------
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

    await update.message.reply_text(r.text)


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
# STATS
# -----------------------------
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")

    r = requests.get(API_URL + "/api/bot/get_keys", params={
        "password": ADMIN_PASSWORD
    })

    keys = r.json()

    active = 0
    expired = 0
    now = datetime.now().date()

    for k in keys:
        exp = datetime.strptime(k["expires"], "%Y-%m-%d").date()
        if exp < now:
            expired += 1
        else:
            active += 1

    await update.message.reply_text(
        f"📊 Key Stats\n"
        f"Active: {active}\n"
        f"Expired: {expired}"
    )


# -----------------------------
# START
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Commands:\n"
        "/check KEY\n"
        "/admin\n\n"
        "Admin Commands:\n"
        "/addkey KEY MAX_DEVICES YYYY-MM-DD\n"
        "/delkey KEY\n"
        "/stats"
    )


# -----------------------------
# MAIN
# -----------------------------
def main():
    TOKEN = "8316549162:AAG3O0KBhuSjFjmuZ0UEedtp_UwPA7J9wMs"

    app = ApplicationBuilder().token(TOKEN).build()

    admin_handler = ConversationHandler(
        entry_points=[CommandHandler("admin", admin_panel)],
        states={ASK_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_password)]},
        fallbacks=[]
    )

    app.add_handler(admin_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("check", check))
    app.add_handler(CommandHandler("addkey", add_key))
    app.add_handler(CommandHandler("delkey", delete_key))
    app.add_handler(CommandHandler("stats", stats))

    print("🤖 Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
