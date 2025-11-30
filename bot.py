import requests
import time
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler

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

def admin_panel(update, context):
    update.message.reply_text("Enter admin password:")
    return ASK_PASS

def admin_password(update, context):
    if update.message.text == ADMIN_PASSWORD:
        ADMIN_LOGGED_IN.add(update.message.from_user.id)
        update.message.reply_text("✅ Logged in as admin!")
    else:
        update.message.reply_text("❌ Wrong password.")

    return ConversationHandler.END

# -----------------------------
# CHECK ADMIN
# -----------------------------
def check_admin(user_id):
    return user_id in ADMIN_LOGGED_IN

# -----------------------------
# ADD KEY
# -----------------------------
def add_key(update, context):
    if not check_admin(update.message.from_user.id):
        return update.message.reply_text("❌ Admin only.")

    if len(context.args) < 3:
        return update.message.reply_text("Usage: /addkey KEY MAX_DEVICES YYYY-MM-DD")

    key = context.args[0]
    max_devices = context.args[1]
    expires = context.args[2]

    r = requests.post(API_URL + "/api/bot/add_key", json={
        "password": ADMIN_PASSWORD,
        "key": key,
        "max_devices": max_devices,
        "expires": expires
    })

    update.message.reply_text(r.text)

# -----------------------------
# DELETE KEY
# -----------------------------
def delete_key(update, context):
    if not check_admin(update.message.from_user.id):
        return update.message.reply_text("❌ Admin only.")

    if len(context.args) < 1:
        return update.message.reply_text("Usage: /delkey KEY")

    key = context.args[0]

    r = requests.post(API_URL + "/api/bot/delete_key", json={
        "password": ADMIN_PASSWORD,
        "key": key
    })

    update.message.reply_text(r.text)

# -----------------------------
# CHECK KEY
# -----------------------------
def check(update, context):
    if len(context.args) < 1:
        return update.message.reply_text("Usage: /check KEY")

    key = context.args[0]

    r = requests.post(API_URL + "/check-key", json={"key": key, "device_id": ""})
    res = r.json()

    if res.get("valid"):
        update.message.reply_text("✅ Key is VALID!")
    else:
        update.message.reply_text(f"❌ Invalid key.\nReason: {res.get('error')}")

# -----------------------------
# STATS
# -----------------------------
def stats(update, context):
    if not check_admin(update.message.from_user.id):
        return update.message.reply_text("❌ Admin only.")

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

    update.message.reply_text(
        f"📊 Key Stats\n"
        f"Active: {active}\n"
        f"Expired: {expired}"
    )

# -----------------------------
# START
# -----------------------------
def start(update, context):
    update.message.reply_text(
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

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    admin_handler = ConversationHandler(
        entry_points=[CommandHandler("admin", admin_panel)],
        states={ASK_PASS: [MessageHandler(Filters.text, admin_password)]},
        fallbacks=[]
    )

    dp.add_handler(admin_handler)
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("check", check))
    dp.add_handler(CommandHandler("addkey", add_key))
    dp.add_handler(CommandHandler("delkey", delete_key))
    dp.add_handler(CommandHandler("stats", stats))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
