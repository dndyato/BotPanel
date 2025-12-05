import requests
import random
import string
from datetime import datetime, timedelta

from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

API_URL = "https://egoistyato.pythonanywhere.com"
ADMIN_PASSWORD = "yato123"

ADMIN_LOGGED_IN = set()
ASK_PASS = 1
WAITING_FILE = {}

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
# ADD KEY (unchanged)
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
# DELETE KEY (unchanged)
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
# CHECK KEY VALIDITY (unchanged)
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
# CHECK INFO (unchanged)
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
        f"🕒 Expires: `{res.get('expires')}`",
        parse_mode="Markdown",
    )

# ---------------------------------------------------
# EXTEND KEY (unchanged)
# ---------------------------------------------------
def parse_days(value):
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
            f"🕒 New Expiry: `{res.get('new_exp')}`",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(f"❌ Error: {res.get('error')}")

# ---------------------------------------------------
# STATS (unchanged)
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
# GENKEY (unchanged)
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
        f"🕒 Expires: `{expiry_text}`\n"
        f"📦 Max Devices: `{max_devices}`\n"
        f"🌐 Site: {API_URL}",
        parse_mode="Markdown"
    )

# ---------------------------------------------------
# NEW: /addfile → wait for file upload
# ---------------------------------------------------
async def addfile(update: Update, context):
    if not check_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")

    WAITING_FILE[update.message.from_user.id] = True
    await update.message.reply_text("📤 Send the `.txt` file you want to upload.")
    
async def file_receiver(update: Update, context):
    uid = update.message.from_user.id

    if uid not in WAITING_FILE:
        return

    del WAITING_FILE[uid]

    doc = update.message.document
    if not doc.file_name.endswith(".txt"):
        return await update.message.reply_text("❌ Only `.txt` allowed.")

    file_bytes = await doc.get_file()
    file_content = await file_bytes.download_as_bytearray()

    r = requests.post(
        API_URL + "/api/bot/upload",
        files={"file": (doc.file_name, file_content)},
        data={"password": ADMIN_PASSWORD},
    )

    res = safe_json(r)
    if res.get("success"):
        await update.message.reply_text(f"✅ Uploaded `{doc.file_name}`")
    else:
        await update.message.reply_text(f"❌ Error: {res.get('error')}")

# ---------------------------------------------------
# NEW: /listfiles
# ---------------------------------------------------
async def listfiles(update: Update, context):
    if not check_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")

    r = requests.get(API_URL + "/api/bot/listfiles")
    res = safe_json(r)

    if not res.get("success"):
        return await update.message.reply_text("❌ Failed to fetch file list.")

    txt = "📁 **Stored Files:**\n\n"
    for f in res["files"]:
        txt += f"• `{f['name']}` — {f['size_kb']} KB — {f['lines']} lines\n"

    await update.message.reply_text(txt, parse_mode="Markdown")

# ---------------------------------------------------
# NEW: /deletefile filename.txt
# ---------------------------------------------------
async def deletefile(update: Update, context):
    if not check_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")

    if len(context.args) < 1:
        return await update.message.reply_text("Usage: /deletefile filename.txt")

    filename = context.args[0]

    r = requests.post(
        API_URL + "/api/bot/deletefile",
        json={"password": ADMIN_PASSWORD, "filename": filename},
    )

    res = safe_json(r)

    if res.get("success"):
        await update.message.reply_text(f"🗑️ Deleted `{filename}`")
    else:
        await update.message.reply_text(f"❌ Error: {res.get('error')}")

# ---------------------------------------------------
# ⭐ NEW FEATURE: /addaccess KEY (save to access.json)
# ---------------------------------------------------
async def addaccess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")

    if len(context.args) < 1:
        return await update.message.reply_text("Usage: /addaccess KEY")

    key = context.args[0]

    # Auto expire after 1 day (you can change this)
    expires = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    payload = {
        "password": ADMIN_PASSWORD,
        "key": key,
        "expires": expires
    }

    r = requests.post(API_URL + "/api/bot/addaccess", json=payload)
    res = safe_json(r)

    if res.get("success"):
        await update.message.reply_text(
            f"🔑 **Access Key Saved!**\n\n"
            f"• Key: `{key}`\n"
            f"• Expires: `{expires}`\n"
            f"• Saved to: `access.json`\n"
            f"🌐 Site: {API_URL}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(f"❌ Error: {res.get('error')}")

# ---------------------------------------------------
# START MESSAGE (unchanged)
# ---------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 **Welcome to Yato Panel Bot!**\n\n"
        "**User Commands:**\n"
        "• `/check KEY`\n"
        "• `/checkinfo KEY`\n\n"
        "**Admin Commands:**\n"
        "• `/admin`\n"
        "• `/addkey`\n"
        "• `/delkey`\n"
        "• `/extend`\n"
        "• `/stats`\n"
        "• `/genkey`\n"
        "• `/addfile`\n"
        "• `/listfiles`\n"
        "• `/deletefile filename.txt`\n"
        "• `/addaccess KEY`  *(new)*",
        parse_mode="Markdown"
    )

# ---------------------------------------------------
# MAIN
# ---------------------------------------------------
def main():
    TOKEN = "8316549162:AAEyrIF02nPnge0b5jDSVPJUcidF8BihBcc"
    app = ApplicationBuilder().token(TOKEN).build()

    admin_conv = ConversationHandler(
        entry_points=[CommandHandler("admin", admin_panel)],
        states={ASK_PASS: [MessageHandler(filters.TEXT, admin_password)]},
        fallbacks=[]
    )

    app.add_handler(admin_conv)

    # normal commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("check", check_key))
    app.add_handler(CommandHandler("checkinfo", check_info))
    app.add_handler(CommandHandler("extend", extend_key))
    app.add_handler(CommandHandler("addkey", add_key))
    app.add_handler(CommandHandler("delkey", delete_key))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("genkey", genkey))

    # NEW /addaccess
    app.add_handler(CommandHandler("addaccess", addaccess))

    # new file commands
    app.add_handler(CommandHandler("addfile", addfile))
    app.add_handler(CommandHandler("listfiles", listfiles))
    app.add_handler(CommandHandler("deletefile", deletefile))

    # receives sent files
    app.add_handler(MessageHandler(filters.Document.ALL, file_receiver))

    print("🤖 Bot Running…")
    app.run_polling()

if __name__ == "__main__":
    main()
