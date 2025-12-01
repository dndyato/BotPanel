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
    await update.message.reply_text("🔐 Enter admin password:")
    return ASK_PASS

async def admin_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == ADMIN_PASSWORD:
        ADMIN_LOGGED_IN.add(update.message.from_user.id)
        await update.message.reply_text("✅ You are now logged in as admin.")
    else:
        await update.message.reply_text("❌ Wrong password.")
    return ConversationHandler.END

def check_admin(uid):
    return uid in ADMIN_LOGGED_IN

# ---------------------------------------------------
# ADD KEY (via API)
# ---------------------------------------------------
async def add_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    if not check_admin(uid):
        return await update.message.reply_text("❌ Admin only. Use /admin to login.")

    if len(context.args) < 3:
        return await update.message.reply_text(
            "Usage:\n/addkey KEY MAX_DEVICES YYYY-MM-DD\n\nExample:\n`/addkey Yato-ABC 1 2025-12-31`",
            parse_mode="Markdown"
        )

    key = context.args[0]
    try:
        max_devices = int(context.args[1])
    except:
        return await update.message.reply_text("❌ `MAX_DEVICES` must be a number.", parse_mode="Markdown")

    expires = context.args[2]

    try:
        r = requests.post(API_URL + "/api/bot/add_key", json={
            "password": ADMIN_PASSWORD,
            "key": key,
            "max_devices": max_devices,
            "expires": expires
        }, timeout=10)
    except Exception as e:
        return await update.message.reply_text(f"⚠️ Error contacting site: {e}")

    # try to parse JSON
    try:
        jr = r.json()
    except Exception:
        return await update.message.reply_text(f"⚠️ Unexpected response from site:\n{r.text}")

    if jr.get("success"):
        await update.message.reply_text(
            f"🔑 **Key Added Successfully!**\n\n"
            f"• Key: `{key}`\n"
            f"• Max Devices: `{max_devices}`\n"
            f"• Expiry: `{expires}`\n\n"
            f"🌐 Site: {API_URL}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(f"❌ Failed to add key: {jr.get('error', r.text)}")

# ---------------------------------------------------
# DELETE KEY (via API)
# ---------------------------------------------------
async def delete_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    if not check_admin(uid):
        return await update.message.reply_text("❌ Admin only. Use /admin to login.")

    if len(context.args) < 1:
        return await update.message.reply_text("Usage: /delkey KEY")

    key = context.args[0]

    try:
        r = requests.post(API_URL + "/api/bot/delete_key", json={
            "password": ADMIN_PASSWORD,
            "key": key
        }, timeout=10)
    except Exception as e:
        return await update.message.reply_text(f"⚠️ Error contacting site: {e}")

    try:
        jr = r.json()
    except Exception:
        return await update.message.reply_text(f"⚠️ Unexpected response from site:\n{r.text}")

    if jr.get("success"):
        await update.message.reply_text(f"🗑️ Key `{key}` deleted successfully.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ Failed to delete key: {jr.get('error', r.text)}")

# ---------------------------------------------------
# CHECK KEY (user)
# ---------------------------------------------------
async def check_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        return await update.message.reply_text("Usage: /check KEY")

    key = context.args[0]

    try:
        r = requests.post(API_URL + "/check-key", json={"key": key, "device_id": ""}, timeout=10)
    except Exception as e:
        return await update.message.reply_text(f"⚠️ Error contacting site: {e}")

    # handle non-json gracefully
    try:
        res = r.json()
    except Exception:
        return await update.message.reply_text(f"⚠️ Unexpected response from site:\n{r.text}")

    if res.get("valid"):
        await update.message.reply_text("✅ Key is *VALID*.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ Invalid key.\nReason: `{res.get('error')}`", parse_mode="Markdown")

# ---------------------------------------------------
# STATS (fixed to use /api/bot/get_keys)
# ---------------------------------------------------
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    if not check_admin(uid):
        return await update.message.reply_text("❌ Admin only. Use /admin to login.")

    try:
        r = requests.post(API_URL + "/api/bot/get_keys", json={"password": ADMIN_PASSWORD}, timeout=10)
    except Exception as e:
        return await update.message.reply_text(f"⚠️ Error contacting site: {e}")

    try:
        keys = r.json()
    except Exception:
        return await update.message.reply_text(f"⚠️ Unexpected response from site:\n{r.text}")

    # basic stats
    total = len(keys)
    active, expired = 0, 0
    now = datetime.now()

    # counts and also small preview of sample keys
    sample_keys = []
    for k in keys:
        exp = k.get("expires", "")
        try:
            exp_date = datetime.strptime(exp, "%Y-%m-%d")
        except:
            try:
                exp_date = datetime.strptime(exp, "%Y-%m-%d %H:%M:%S")
            except:
                # if parsing fails treat as active
                exp_date = now + timedelta(days=3650)

        if exp_date < now:
            expired += 1
        else:
            active += 1

        if len(sample_keys) < 6:
            sample_keys.append(k.get("key"))

    sample_text = "\n".join(f"`{s}`" for s in sample_keys) if sample_keys else "—"

    await update.message.reply_text(
        "📊 *Key Stats*\n\n"
        f"• Total keys: `{total}`\n"
        f"• Active: `{active}`\n"
        f"• Expired: `{expired}`\n\n"
        f"🔎 Sample keys:\n{sample_text}\n\n"
        f"🌐 Site: {API_URL}",
        parse_mode="Markdown"
    )

# ---------------------------------------------------
# GENKEY (already used /api/bot/add_key correctly)
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
        return await update.message.reply_text("❌ Admin only. Use /admin to login.")

    if len(context.args) < 3:
        return await update.message.reply_text(
            "Usage:\n`/genkey AMOUNT DURATION MAX_DEVICES`\nExample: `/genkey 5 1d 1`",
            parse_mode="Markdown"
        )

    try:
        amount = int(context.args[0])
    except:
        return await update.message.reply_text("❌ `AMOUNT` must be a number.", parse_mode="Markdown")

    duration = parse_duration(context.args[1])
    try:
        max_devices = int(context.args[2])
    except:
        return await update.message.reply_text("❌ `MAX_DEVICES` must be a number.", parse_mode="Markdown")

    if not duration:
        return await update.message.reply_text("❌ Invalid duration. Use `1d`, `2h`, `30m`", parse_mode="Markdown")

    expiry = datetime.now() + duration
    expiry_text = expiry.strftime("%Y-%m-%d %H:%M:%S")

    generated = []

    for _ in range(amount):
        key = "Yato-" + random_suffix()
        generated.append(key)

        # call API
        try:
            requests.post(API_URL + "/api/bot/add_key", json={
                "password": ADMIN_PASSWORD,
                "key": key,
                "max_devices": max_devices,
                "expires": expiry_text
            }, timeout=10)
        except Exception:
            # ignore single failures but continue
            pass

    msg = "\n".join(f"`{k}`" for k in generated)

    await update.message.reply_text(
        f"🎉 *Generated {amount} Keys!*\n\n"
        f"{msg}\n\n"
        f"⏳ Duration: `{context.args[1]}`\n"
        f"📅 Expires: `{expiry_text}`\n"
        f"📦 Max Devices: `{max_devices}`\n\n"
        f"🌐 Site: {API_URL}",
        parse_mode="Markdown"
    )

# ---------------------------------------------------
# START
# ---------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome!\n\n"
        "/check KEY — Check a key\n"
        "/admin — Admin login\n\n"
        "Admin Commands (after /admin):\n"
        "/addkey KEY MAX_DEVICES YYYY-MM-DD\n"
        "/delkey KEY\n"
        "/stats\n"
        "/genkey AMOUNT DURATION MAX_DEVICES\n\n"
        f"Site: {API_URL}"
    )

# ---------------------------------------------------
# MAIN
# ---------------------------------------------------
def main():
    TOKEN = "8316549162:AAG3O0KBhuSjFjmuZ0UEedtp_UwPA7J9wMs"
    app = ApplicationBuilder().token(TOKEN).build()

    admin_conv = ConversationHandler(
        entry_points=[CommandHandler("admin", admin_panel)],
        states={ASK_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_password)]},
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
