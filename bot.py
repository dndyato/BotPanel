from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
import requests
import random
import string
from datetime import datetime, timedelta

from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ChatMemberHandler, ConversationHandler, ContextTypes, filters
)

API_URL = "https://egoistyato.pythonanywhere.com"
ADMIN_PASSWORD = "yato123"

ADMIN_LOGGED_IN = set()
ASK_PASS = 1
WAITING_FILE = {}
WAITING_BROADCAST = {}  # <-- ADDED


# ---------------------------------------------------
# BROADCAST ADMIN GROUPS TRACKER
# ---------------------------------------------------
ADMIN_GROUPS = set()  # groups where bot is admin


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
# USER DOMAIN REQUEST SYSTEM
# ---------------------------------------------------
import json, os

REQUEST_FILE = "domain_requests.json"

if not os.path.exists(REQUEST_FILE):
    with open(REQUEST_FILE, "w") as f:
        json.dump({"requests": []}, f, indent=4)

def save_request(user_id, username, domain):
    with open(REQUEST_FILE, "r") as f:
        data = json.load(f)

    data["requests"].append({
        "user_id": user_id,
        "username": username,
        "domain": domain,
        "time": str(datetime.now())
    })

    with open(REQUEST_FILE, "w") as f:
        json.dump(data, f, indent=4)


async def request_domain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        return await update.message.reply_text(
            "📩 *Usage:*\n`/requests domain.com`",
            parse_mode="Markdown"
        )

    domain = " ".join(context.args)
    user = update.message.from_user

    save_request(user.id, user.username, domain)

    BOT_ADMIN_CHAT = 7675369659

    text = (
        "📥 *NEW DOMAIN REQUEST*\n\n"
        f"👤 User: `{user.id}`\n"
        f"🧑 Username: @{user.username}\n"
        f"🌐 Domain: `{domain}`\n"
        f"🕒 Time: `{datetime.now()}`"
    )

    try:
        await context.bot.send_message(chat_id=BOT_ADMIN_CHAT, text=text, parse_mode="Markdown")
    except:
        pass

    await update.message.reply_text(
        "✅ Your domain request has been sent!",
        parse_mode="Markdown"
    )


async def all_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")

    with open(REQUEST_FILE, "r") as f:
        data = json.load(f).get("requests", [])

    if not data:
        return await update.message.reply_text("📭 No requests found.")

    msg = "📚 *ALL DOMAIN REQUESTS:*\n\n"

    for r in data[-50:]:
        msg += (
            f"👤 `{r['user_id']}` | @{r['username']}\n"
            f"🌐 `{r['domain']}`\n"
            f"🕒 {r['time']}\n"
            "━━━━━━━━━━━━━━\n"
        )

    await update.message.reply_text(msg, parse_mode="Markdown")



# ---------------------------------------------------
# ADD KEY
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
# DELETE KEY
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
# CHECK KEY
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
# CHECKINFO
# ---------------------------------------------------
async def check_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        return await update.message.reply_text("Usage: /checkinfo KEY")

    key = context.args[0]

    r = requests.get(API_URL + "/api/bot/checkinfo", params={"key": key})
    res = safe_json(r)

    if not res.get("success"):
        return await update.message.reply_text(
            f"❌ Error: `{res.get('error')}`",
            parse_mode="Markdown"
        )

    await update.message.reply_text(
        "🔍 **Key Information**\n\n"
        f"🔑 Key: `{res.get('key')}`\n"
        f"📦 Max Devices: `{res.get('max_devices')}`\n"
        f"📱 Used Devices: `{res.get('used_devices')}`\n"
        f"⏳ Expires: `{res.get('expires')}`",
        parse_mode="Markdown",
    )


# ---------------------------------------------------
# EXTEND KEY
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
            f"⏰ New Expiry: `{res.get('new_exp')}`",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(f"❌ Error: {res.get('error')}")


# ---------------------------------------------------
# STATS
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
# GENKEY
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
# FILE UPLOAD + BROADCAST
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
    if not res.get("success"):
        return await update.message.reply_text(f"❌ Error: {res.get('error')}")

    # FILE DETAILS
    fname = doc.file_name
    size_kb = round(len(file_content) / 1024, 2)
    line_count = file_content.decode("utf-8", errors="ignore").count("\n")

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")

    # BROADCAST MESSAGE
    msg = (
        "📢 **New Data Added**\n"
        "🚀 Fresh logs are now live – enjoy the latest results!\n"
        "━━━━━━━━━━━━━━━\n\n"
        f"📊 **Lines:** `{line_count}`\n"
        f"📅 **Added:** `{date_str}`\n"
        f"⏰ **Time:** `{time_str}`\n"
        "✅ **Status:** Ready to search!\n"
        "📤 **Export:** Available\n\n"
        f"📁 **File:** `{fname}`\n"
        f"💾 **Size:** `{size_kb} KB`\n"
        "━━━━━━━━━━━━━━━\n"
        "Search now to generate accounts from these fresh rows! 🚀"
    )

    # SEND TO ALL ADMIN GROUPS
    for gid in list(ADMIN_GROUPS):
        try:
            await context.bot.send_message(chat_id=gid, text=msg, parse_mode="Markdown")
        except:
            pass

    await update.message.reply_text(f"✅ Uploaded `{doc.file_name}` and broadcast sent!")


# ---------------------------------------------------
# LIST FILES
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
        txt += f"• `{f['name']}` — {f['size_kb']} KB — {f['lines']} lines\n"  # <-- fixed

    await update.message.reply_text(txt, parse_mode="Markdown")

# ---------------------------------------------------
# DELETE FILE
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
# ADDACCESS
# ---------------------------------------------------
async def addaccess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")

    if len(context.args) < 1:
        return await update.message.reply_text("Usage: /addaccess KEY")

    key = context.args[0]
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
# MULTILINE BROADCAST RECEIVER (FIXED)
# ---------------------------------------------------
async def broadcast_receiver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id

    if uid not in WAITING_BROADCAST:
        return

    del WAITING_BROADCAST[uid]

    # Forward the exact message as sent
    msg = update.message.text  # no .to_dict(), just take the text

    if not ADMIN_GROUPS:
        return await update.message.reply_text("⚠️ No admin groups detected!")

    sent = 0
    for gid in list(ADMIN_GROUPS):
        try:
            await context.bot.send_message(chat_id=gid, text=msg)
            sent += 1
        except:
            pass

    await update.message.reply_text(f"📢 Multiline broadcast sent to **{sent}** groups.")


# ---------------------------------------------------
# BROADCAST CUSTOM MESSAGE (MULTILINE) FIXED
# ---------------------------------------------------
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")

    # If no args, enable multiline mode
    if not context.args:
        WAITING_BROADCAST[update.message.from_user.id] = True
        return await update.message.reply_text(
            "📝 *Send the full broadcast message now.*\n"
            "It will be forwarded exactly as you type.",
            parse_mode="Markdown"
        )

    # Single-line mode, join args with spaces
    msg = " ".join(context.args)

    if not ADMIN_GROUPS:
        return await update.message.reply_text("⚠️ No admin groups detected!")

    sent = 0
    for gid in list(ADMIN_GROUPS):
        try:
            await context.bot.send_message(chat_id=gid, text=msg)
            sent += 1
        except:
            pass

    await update.message.reply_text(f"📢 Broadcast sent to **{sent}** groups.")

# ---------------------------------------------------
# TEST BROADCAST
# ---------------------------------------------------
async def testbroadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")

    if not ADMIN_GROUPS:
        return await update.message.reply_text("⚠️ No admin groups detected!")

    msg = (
        "🧪 **Test Broadcast**\n"
        "━━━━━━━━━━━━━━━\n"
        "This is a test broadcast message.\n"
        "If you see this, broadcast is working!\n"
        "━━━━━━━━━━━━━━━"
    )

    count = 0
    for gid in list(ADMIN_GROUPS):
        try:
            await context.bot.send_message(chat_id=gid, text=msg, parse_mode="Markdown")
            count += 1
        except:
            pass

    await update.message.reply_text(f"✅ Test broadcast sent to **{count}** groups.")

async def deny_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")

    if len(context.args) < 2:
        return await update.message.reply_text(
            "Usage: /denyrequest <number> <reason>"
        )

    try:
        index = int(context.args[0]) - 1
    except:
        return await update.message.reply_text("❌ Invalid request number.")

    reason = " ".join(context.args[1:])

    with open(REQUEST_FILE, "r") as f:
        data = json.load(f)

    requests_list = data.get("requests", [])

    if index < 0 or index >= len(requests_list):
        return await update.message.reply_text("❌ Request not found.")

    req = requests_list.pop(index)

    with open(REQUEST_FILE, "w") as f:
        json.dump(data, f, indent=4)

    # notify user
    try:
        await context.bot.send_message(
            chat_id=req["user_id"],
            text=(
                "❌ **DOMAIN REQUEST DENIED**\n\n"
                f"🌐 Domain: `{req['domain']}`\n"
                f"📄 Reason: *{reason}*"
            ),
            parse_mode="Markdown"
        )
    except:
        pass

    await update.message.reply_text(
        f"🚫 Denied request:\n`{req['domain']}`\nReason: {reason}",
        parse_mode="Markdown"
    )
    
async def approve_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")

    if len(context.args) < 1:
        return await update.message.reply_text(
            "Usage: /approverequest <number>"
        )

    try:
        index = int(context.args[0]) - 1
    except:
        return await update.message.reply_text("❌ Invalid request number.")

    with open(REQUEST_FILE, "r") as f:
        data = json.load(f)

    requests_list = data.get("requests", [])

    if index < 0 or index >= len(requests_list):
        return await update.message.reply_text("❌ Request not found.")

    req = requests_list.pop(index)

    with open(REQUEST_FILE, "w") as f:
        json.dump(data, f, indent=4)

    # notify user
    try:
        await context.bot.send_message(
            chat_id=req["user_id"],
            text=(
                "✅ **DOMAIN APPROVED!**\n\n"
                f"🌐 Domain: `{req['domain']}`\n"
                "🎉 Your request has been approved!"
            ),
            parse_mode="Markdown"
        )
    except:
        pass

    await update.message.reply_text(
        f"✅ Approved request:\n`{req['domain']}`",
        parse_mode="Markdown"
    )

# ---------------------------------------------------
# TRACK BOT STATUS (ADMIN ONLY)
# ---------------------------------------------------
async def track_bot_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    status = update.my_chat_member.new_chat_member.status

    if chat.type in ["group", "supergroup"]:
        if status == "administrator":
            ADMIN_GROUPS.add(chat.id)
        else:
            ADMIN_GROUPS.discard(chat.id)

async def download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not check_admin(query.from_user.id):
        return await query.message.reply_text("❌ Admin only.")

    if not query.data.startswith("DL|"):
        return

    filename = query.data.split("|", 1)[1]

    url = (
        f"{API_URL}/api/bot/download"
        f"?password={ADMIN_PASSWORD}&filename={filename}"
    )

    try:
        r = requests.get(url, stream=True)
    except:
        return await query.message.reply_text("❌ Server unreachable.")

    if r.status_code != 200:
        return await query.message.reply_text("❌ File not found or denied.")

    tmp = f"/tmp/{filename}"
    with open(tmp, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)

    await query.message.reply_document(
        document=open(tmp, "rb"),
        filename=filename,
        caption=f"📥 **Downloaded from database**\n`{filename}`",
        parse_mode="Markdown"
    )

async def download_picker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")

    r = requests.get(API_URL + "/api/bot/listfiles")
    res = safe_json(r)

    if not res.get("success") or not res.get("files"):
        return await update.message.reply_text("📭 No files available.")

    keyboard = []
    for f in res["files"]:
        keyboard.append([
            InlineKeyboardButton(
                text=f"📄 {f['name']} ({f['lines']} lines)",
                callback_data=f"DL|{f['name']}"
            )
        ])

    await update.message.reply_text(
        "📂 **Select a file to download:**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ---------------------------------------------------
# START MESSAGE
# ---------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 **Welcome to Yato Panel Bot!**\n\n"
        "**User Commands:**\n"
        "• `/check KEY`\n"
        "• `/checkinfo KEY`\n"
        "• `/requests domain`\n\n"
        "**Admin Commands:**\n"
        "• `/admin`\n"
        "• `/addkey`\n"
        "• `/delkey`\n"
        "• `/extend`\n"
        "• `/stats`\n"
        "• `/genkey`\n"
        "• `/addfile`\n"
        "• `/listfiles`\n"
        "• `/download`\n"
        "• `/deletefile filename.txt`\n"
        "• `/addaccess KEY`\n"
        "• `/allrequests`\n"
        "• `/broadcast`\n"
        "• `/testbroadcast`\n"
        "• `/approverequest`\n"
        "• `/denyrequest`\n",
        parse_mode="Markdown"
    )


# ---------------------------------------------------
# MAIN
# ---------------------------------------------------
def main():
    TOKEN = "8316549162:AAF7v5QYd0RgdbHPu554A6Cd-0VIWYhRXuQ"

    app = ApplicationBuilder().token(TOKEN).build()

    admin_conv = ConversationHandler(
        entry_points=[CommandHandler("admin", admin_panel)],
        states={ASK_PASS: [MessageHandler(filters.TEXT, admin_password)]},
        fallbacks=[]
    )

    app.add_handler(admin_conv)

    # commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("check", check_key))
    app.add_handler(CommandHandler("checkinfo", check_info))
    app.add_handler(CommandHandler("extend", extend_key))
    app.add_handler(CommandHandler("addkey", add_key))
    app.add_handler(CommandHandler("delkey", delete_key))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("genkey", genkey))
    app.add_handler(CommandHandler("addaccess", addaccess))
    app.add_handler(CommandHandler("testbroadcast", testbroadcast))
    app.add_handler(CommandHandler("broadcast", broadcast))

    # REQUEST SYSTEM
    app.add_handler(CommandHandler("requests", request_domain))
    app.add_handler(CommandHandler("allrequests", all_requests))
    app.add_handler(CommandHandler("approverequest", approve_request))
    app.add_handler(CommandHandler("denyrequest", deny_request))

    # file management
    app.add_handler(CommandHandler("addfile", addfile))
    app.add_handler(CommandHandler("listfiles", listfiles))
    app.add_handler(CommandHandler("deletefile", deletefile))
    app.add_handler(MessageHandler(filters.Document.ALL, file_receiver))
    app.add_handler(CommandHandler("download", download_picker))
    app.add_handler(CallbackQueryHandler(download_callback))

    # MULTILINE BROADCAST RECEIVER
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_receiver))

    # admin tracking
    app.add_handler(ChatMemberHandler(track_bot_status, ChatMemberHandler.MY_CHAT_MEMBER))

    print("🤖 Bot Running…")
    app.run_polling()


if __name__ == "__main__":
    main()
