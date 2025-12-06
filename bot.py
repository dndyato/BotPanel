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

TOKEN = "8316549162:AAEtHGLTkAZq2QJTSOZcfKQAbyVYZi4bb6w"

ADMIN_LOGGED_IN = set()
ASK_PASS = 1
WAITING_FILE = {}

# ----------- STORAGE (groups auto-broadcast) -------------
import json
GROUPS_FILE = "groups.json"

def load_groups():
    try:
        return json.load(open(GROUPS_FILE, "r"))
    except:
        return []

def save_groups(groups):
    json.dump(groups, open(GROUPS_FILE, "w"), indent=4)

groups_list = load_groups()

# ---------------- SAFE JSON ----------------
def safe_json(r):
    try:
        return r.json()
    except:
        return {"success": False, "error": "Invalid JSON response from server"}

# ---------------- ADMIN ----------------
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

# ---------------- BROADCAST FUNCTION ----------------
async def broadcast(text, app):
    remove = []
    for gid in groups_list:
        try:
            await app.bot.send_message(gid, text)
        except:
            remove.append(gid)
    if remove:
        for r in remove:
            groups_list.remove(r)
        save_groups(groups_list)

# ---------------- AUTO SAVE GROUPS ----------------
async def handle_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.message.chat
    if chat.type in ["group", "supergroup"]:
        if chat.id not in groups_list:
            groups_list.append(chat.id)
            save_groups(groups_list)
            await update.message.reply_text("📡 Group registered for broadcasts!")

# ---------------- ADD KEY ----------------
async def add_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")
    
    if len(context.args) < 3:
        return await update.message.reply_text("Usage: /addkey KEY MAX_DEVICES YYYY-MM-DD")

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
            f"🔑 Key Added!\n• {key}\n• Max: {max_devices}\n• Expires: {expires}"
        )
    else:
        await update.message.reply_text(f"❌ {res.get('error')}")

# ---------------- DELETE KEY ----------------
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
        await update.message.reply_text(f"🗑️ Deleted: {key}")
    else:
        await update.message.reply_text(f"❌ {res.get('error')}")

# ---------------- CHECK KEY ----------------
async def check_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        return await update.message.reply_text("Usage: /check KEY")

    key = context.args[0]

    r = requests.post(API_URL + "/check-key", json={"key": key, "device_id": ""})
    res = safe_json(r)

    if res.get("valid"):
        await update.message.reply_text("✅ VALID KEY")
    else:
        await update.message.reply_text(f"❌ {res.get('error')}")

# ---------------- CHECK INFO ----------------
async def check_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        return await update.message.reply_text("Usage: /checkinfo KEY")

    key = context.args[0]

    r = requests.get(API_URL + "/api/bot/checkinfo", params={"key": key})
    res = safe_json(r)

    if not res.get("success"):
        return await update.message.reply_text(f"❌ {res.get('error')}")

    txt = (
        "🔍 Key Info\n\n"
        f"Key: {res['key']}\n"
        f"Max Devices: {res['max_devices']}\n"
        f"Used: {res['used_devices']}\n"
        f"Expires: {res['expires']}"
    )
    await update.message.reply_text(txt)

# ---------------- EXTEND ----------------
def parse_days(value):
    v = value.lower()
    if v.endswith("d"):
        return int(v[:-1])
    return int(v)

async def extend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")
    
    if len(context.args) < 2:
        return await update.message.reply_text("Usage: /extend KEY DAYS")

    key = context.args[0]
    days = parse_days(context.args[1])

    r = requests.post(API_URL + "/api/bot/extend", json={
        "password": ADMIN_PASSWORD,
        "key": key,
        "days": days
    })
    res = safe_json(r)

    if res.get("success"):
        await update.message.reply_text(f"⏳ Extended! New Exp: {res['new_exp']}")
    else:
        await update.message.reply_text(f"❌ {res.get('error')}")

# ---------------- STATS (MISSING FIXED HERE) ----------------
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")

    r = requests.get(API_URL + "/api/bot/stats")
    res = safe_json(r)

    if not isinstance(res, list):
        return await update.message.reply_text("❌ Server error")

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
        f"📊 Stats\n\nTotal: {total}\nActive: {active}\nExpired: {expired}"
    )

# ---------------- GENKEY ----------------
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
        return await update.message.reply_text("Usage: /genkey AMOUNT 1d MAX_DEVICES")

    amount = int(context.args[0])
    duration = parse_duration(context.args[1])
    max_devices = int(context.args[2])

    expiry = datetime.now() + duration
    exp_text = expiry.strftime("%Y-%m-%d %H:%M:%S")

    keys = []
    for _ in range(amount):
        key = "Yato-" + random_suffix()
        keys.append(key)
        requests.post(API_URL + "/api/bot/add_key", json={
            "password": ADMIN_PASSWORD,
            "key": key,
            "max_devices": max_devices,
            "expires": exp_text
        })

    out = "\n".join(keys)
    await update.message.reply_text(f"Generated:\n{out}")

# ---------------- ADD ACCESS ----------------
async def addaccess(update: Update, context):
    if not check_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")
    
    if len(context.args) < 1:
        return await update.message.reply_text("Usage: /addaccess KEY")

    key = context.args[0]
    expires = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    r = requests.post(API_URL + "/api/bot/addaccess", json={
        "password": ADMIN_PASSWORD,
        "key": key,
        "expires": expires
    })
    res = safe_json(r)

    if res.get("success"):
        await update.message.reply_text(
            f"🔑 Access added!\nKey: {key}\nExpires: {expires}"
        )
    else:
        await update.message.reply_text(f"❌ {res.get('error')}")

# ---------------- WAIT FOR FILE ----------------
async def addfile(update: Update, context):
    if not check_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")
    WAITING_FILE[update.message.from_user.id] = True
    await update.message.reply_text("📤 Send `.txt` file now.")

# ---------------- FILE RECEIVER ----------------
async def file_receiver(update: Update, context):
    uid = update.message.from_user.id
    
    if uid not in WAITING_FILE:
        return
    
    del WAITING_FILE[uid]

    doc = update.message.document
    if not doc.file_name.endswith(".txt"):
        return await update.message.reply_text("❌ Only `.txt` allowed.")

    file_obj = await doc.get_file()
    file_bytes = await file_obj.download_as_bytearray()

    r = requests.post(
        API_URL + "/api/bot/upload",
        files={"file": (doc.file_name, file_bytes)},
        data={"password": ADMIN_PASSWORD},
    )
    res = safe_json(r)

    if not res.get("success"):
        return await update.message.reply_text(f"❌ {res.get('error')}")

    text = file_bytes.decode("utf-8", errors="ignore")
    lines = len([l for l in text.splitlines() if l.strip()])
    size_kb = round(len(file_bytes) / 1024, 2)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    broadcast_msg = (
        "📢 **New Data Added!**\n"
        "🚀 Fresh logs are now live!\n"
        "━━━━━━━━━━━━━━━\n"
        f"📊 **Lines:** {lines}\n"
        f"📅 **Added:** {now}\n"
        f"💾 **Size:** {size_kb} KB\n"
        "⏰ **Status:** Ready to search!\n"
        "📤 Export available.\n\n"
        f"📁 **File:** `{doc.file_name}`\n"
        "━━━━━━━━━━━━━━━\n"
        "🔥 Search now to generate fresh accounts!"
    )

    await update.message.reply_text(f"✅ Uploaded `{doc.file_name}`!")
    await broadcast(broadcast_msg, context.application)

# ---------------- LIST FILES ----------------
async def listfiles(update: Update, context):
    if not check_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")

    r = requests.get(API_URL + "/api/bot/listfiles")
    res = safe_json(r)

    if not res.get("success"):
        return await update.message.reply_text("❌ Server error.")

    out = "📁 **Stored Files**\n\n"
    for f in res["files"]:
        out += f"• `{f['name']}` — {f['size_kb']} KB — {f['lines']} lines\n"

    await update.message.reply_text(out)

# ---------------- DELETE FILE ----------------
async def deletefile(update: Update, context):
    if not check_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")

    if len(context.args) < 1:
        return await update.message.reply_text("Usage: /deletefile filename.txt")

    filename = context.args[0]

    r = requests.post(
        API_URL + "/api/bot/deletefile",
        json={"password": ADMIN_PASSWORD, "filename": filename}
    )
    res = safe_json(r)

    if res.get("success"):
        await update.message.reply_text(f"🗑️ Deleted `{filename}`")
    else:
        await update.message.reply_text(f"❌ {res.get('error')}")

# ---------------- START MSG ----------------
async def start(update: Update, context):
    await update.message.reply_text(
        "👋 **Welcome to Yato Panel Bot**\n\n"
        "**User:**\n"
        "• `/check KEY`\n"
        "• `/checkinfo KEY`\n\n"
        "**Admin:**\n"
        "• `/admin`\n"
        "• `/addkey`\n"
        "• `/delkey`\n"
        "• `/extend`\n"
        "• `/stats`\n"
        "• `/genkey`\n"
        "• `/addfile`\n"
        "• `/deletefile`\n"
        "• `/addaccess`\n"
        "• `/listfiles`"
    )

# ---------------- MAIN ----------------
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    admin_conv = ConversationHandler(
        entry_points=[CommandHandler("admin", admin_panel)],
        states={ASK_PASS: [MessageHandler(filters.TEXT, admin_password)]},
        fallbacks=[]
    )
    app.add_handler(admin_conv)

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_group))
    app.add_handler(MessageHandler(filters.ALL & filters.Regex(".*"), handle_group))

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("check", check_key))
    app.add_handler(CommandHandler("checkinfo", check_info))
    app.add_handler(CommandHandler("extend", extend))
    app.add_handler(CommandHandler("addkey", add_key))
    app.add_handler(CommandHandler("delkey", delete_key))
    app.add_handler(CommandHandler("stats", stats))   # FIXED
    app.add_handler(CommandHandler("genkey", genkey))
    app.add_handler(CommandHandler("addaccess", addaccess))

    app.add_handler(CommandHandler("addfile", addfile))
    app.add_handler(CommandHandler("listfiles", listfiles))
    app.add_handler(CommandHandler("deletefile", deletefile))
    app.add_handler(MessageHandler(filters.Document.ALL, file_receiver))

    print("🤖 Bot Running…")
    app.run_polling()

if __name__ == "__main__":
    main()
