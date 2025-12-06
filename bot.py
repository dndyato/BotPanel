import requests
import random
import string
from datetime import datetime, timedelta

from telegram import Update, ChatMemberUpdated
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters, ChatMemberHandler
)

API_URL = "https://egoistyato.pythonanywhere.com"
ADMIN_PASSWORD = "yato123"

ADMIN_LOGGED_IN = set()
WAITING_FILE = {}
ASK_PASS = 1

# Store only groups where bot is admin
ADMIN_GROUPS = set()


# ---------------------------------------------------
# SAFE JSON PARSER
# ---------------------------------------------------
def safe_json(r):
    try:
        return r.json()
    except:
        return {"success": False, "error": "Invalid JSON from server"}


# ---------------------------------------------------
# ADMIN LOGIN
# ---------------------------------------------------
async def admin_panel(update: Update, context):
    await update.message.reply_text("🔐 Enter admin password:")
    return ASK_PASS

async def admin_password(update: Update, context):
    if update.message.text == ADMIN_PASSWORD:
        ADMIN_LOGGED_IN.add(update.message.from_user.id)
        await update.message.reply_text("✅ Admin access granted!")
    else:
        await update.message.reply_text("❌ Wrong password.")
    return ConversationHandler.END

def is_admin(uid):
    return uid in ADMIN_LOGGED_IN


# ---------------------------------------------------
# BASIC COMMANDS
# ---------------------------------------------------
async def start(update: Update, context):
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
        "• `/addaccess KEY`",
        parse_mode="Markdown"
    )


# ---------------------------------------------------
# KEY MANAGEMENT
# ---------------------------------------------------
async def add_key(update: Update, context):
    if not is_admin(update.message.from_user.id):
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
        await update.message.reply_text(f"🔑 Key `{key}` added!")
    else:
        await update.message.reply_text(f"❌ Error: {res.get('error')}")


async def delete_key(update: Update, context):
    if not is_admin(update.message.from_user.id):
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
        await update.message.reply_text(f"🗑 Key `{key}` deleted.")
    else:
        await update.message.reply_text(f"❌ Error: {res.get('error')}")


async def check_key(update: Update, context):
    if len(context.args) < 1:
        return await update.message.reply_text("Usage: /check KEY")

    key = context.args[0]
    r = requests.post(API_URL + "/check-key", json={"key": key, "device_id": ""})
    res = safe_json(r)

    if res.get("valid"):
        await update.message.reply_text("✅ Valid key!")
    else:
        await update.message.reply_text(f"❌ Invalid: {res.get('error')}")


async def check_info(update: Update, context):
    if len(context.args) < 1:
        return await update.message.reply_text("Usage: /checkinfo KEY")

    key = context.args[0]
    r = requests.get(API_URL + "/api/bot/checkinfo", params={"key": key})
    res = safe_json(r)

    if not res.get("success"):
        return await update.message.reply_text(f"❌ {res.get('error')}")

    await update.message.reply_text(
        f"🔍 Key Info:\n"
        f"🔑 `{res['key']}`\n"
        f"📦 Max Devices: {res['max_devices']}\n"
        f"📱 Used: {res['used_devices']}\n"
        f"⏳ Expires: {res['expires']}",
        parse_mode="Markdown"
    )


async def extend_key(update: Update, context):
    if not is_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")

    if len(context.args) < 2:
        return await update.message.reply_text("Usage: /extend KEY DAYS")

    key = context.args[0]
    days = int(context.args[1])

    r = requests.post(API_URL + "/api/bot/extend", json={
        "password": ADMIN_PASSWORD,
        "key": key,
        "days": days
    })
    res = safe_json(r)

    if res.get("success"):
        await update.message.reply_text(f"⏳ Extended!\nNew Expiry: {res['new_exp']}")
    else:
        await update.message.reply_text(f"❌ {res.get('error')}")


async def stats(update: Update, context):
    if not is_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")

    r = requests.get(API_URL + "/api/bot/stats")
    res = safe_json(r)

    if not isinstance(res, list):
        return await update.message.reply_text("❌ Error reading stats")

    now = datetime.now()
    active = 0
    expired = 0

    for k in res:
        try:
            exp = datetime.strptime(k["expires"], "%Y-%m-%d")
        except:
            exp = datetime.strptime(k["expires"], "%Y-%m-%d %H:%M:%S")

        (expired if exp < now else active).__add__(1)

    await update.message.reply_text(
        f"📊 Stats:\nActive: {active}\nExpired: {expired}"
    )


# ---------------------------------------------------
# GENKEY
# ---------------------------------------------------
def random_suffix(l=10):
    import string, random
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(l))

async def genkey(update: Update, context):
    if not is_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")

    if len(context.args) < 3:
        return await update.message.reply_text("Usage: /genkey AMOUNT DURATION MAX_DEVICES")

    amount = int(context.args[0])
    duration = context.args[1]
    max_devices = int(context.args[2])

    if duration.endswith("d"):
        delta = timedelta(days=int(duration[:-1]))
    elif duration.endswith("h"):
        delta = timedelta(hours=int(duration[:-1]))
    else:
        return await update.message.reply_text("❌ Invalid duration (use 1d or 10h)")

    expiry = datetime.now() + delta
    expire_txt = expiry.strftime("%Y-%m-%d %H:%M:%S")

    generated = []
    for _ in range(amount):
        key = "Yato-" + random_suffix()
        generated.append(key)
        requests.post(API_URL + "/api/bot/add_key", json={
            "password": ADMIN_PASSWORD,
            "key": key,
            "max_devices": max_devices,
            "expires": expire_txt
        })

    await update.message.reply_text(
        "🎉 **Generated Keys:**\n" +
        "\n".join(f"`{k}`" for k in generated),
        parse_mode="Markdown"
    )


# ---------------------------------------------------
# ACCESS SAVE
# ---------------------------------------------------
async def addaccess(update: Update, context):
    if not is_admin(update.message.from_user.id):
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
        await update.message.reply_text(f"🔑 Access Saved: `{key}`", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ {res.get('error')}")


# ---------------------------------------------------
# FILE UPLOAD + BROADCAST
# ---------------------------------------------------
async def addfile(update: Update, context):
    if not is_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")
    WAITING_FILE[update.message.from_user.id] = True
    await update.message.reply_text("📤 Send the `.txt` file.")


async def file_receiver(update: Update, context):
    uid = update.message.from_user.id
    if uid not in WAITING_FILE:
        return
    del WAITING_FILE[uid]

    doc = update.message.document
    if not doc.file_name.endswith(".txt"):
        return await update.message.reply_text("❌ Only .txt allowed.")

    file_obj = await doc.get_file()
    file_bytes = await file_obj.download_as_bytearray()

    # upload to server
    r = requests.post(API_URL + "/api/bot/upload",
        files={"file": (doc.file_name, file_bytes)},
        data={"password": ADMIN_PASSWORD}
    )
    res = safe_json(r)

    if not res.get("success"):
        return await update.message.reply_text(f"❌ Upload failed: {res.get('error')}")

    # calculate info
    fname = doc.file_name
    size_kb = round(len(file_bytes) / 1024, 2)
    line_count = file_bytes.decode("utf-8", errors="ignore").count("\n")
    now = datetime.now()

    msg = (
        "📢 **New Data Added**\n"
        "🚀 Fresh logs are now live!\n"
        "━━━━━━━━━━━━━━━\n\n"
        f"📊 **Lines:** `{line_count}`\n"
        f"📅 **Added:** `{now.strftime('%Y-%m-%d')}`\n"
        f"⏰ **Time:** `{now.strftime('%H:%M:%S')}`\n"
        "✅ **Status:** Ready to search!\n"
        "📤 **Export:** Available\n\n"
        f"📁 **File:** `{fname}`\n"
        f"💾 **Size:** `{size_kb} KB`\n"
        "━━━━━━━━━━━━━━━\n"
        "Search now to generate accounts from these fresh rows! 🚀"
    )

    # broadcast ONLY in admin groups
    for gid in ADMIN_GROUPS:
        try:
            await context.bot.send_message(gid, msg, parse_mode="Markdown")
        except:
            pass

    await update.message.reply_text(f"✅ Uploaded `{fname}` and broadcast sent!")


# ---------------------------------------------------
# TRACK BOT ADMIN STATUS IN GROUPS
# ---------------------------------------------------
async def track_bot_status(update: ChatMemberUpdated, context):

    chat = update.effective_chat
    member = update.new_chat_member

    if chat.type not in ["group", "supergroup"]:
        return

    if member.user.id != context.bot.id:
        return

    # bot removed
    if member.status in ["left", "kicked"]:
        if chat.id in ADMIN_GROUPS:
            ADMIN_GROUPS.remove(chat.id)
        return

    # bot admin
    if member.status == "administrator":
        ADMIN_GROUPS.add(chat.id)
        return

    # bot not admin → auto-leave
    try:
        await context.bot.leave_chat(chat.id)
    except:
        pass

    if chat.id in ADMIN_GROUPS:
        ADMIN_GROUPS.remove(chat.id)


# ---------------------------------------------------
# LIST + DELETE FILES
# ---------------------------------------------------
async def listfiles(update: Update, context):
    if not is_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")

    r = requests.get(API_URL + "/api/bot/listfiles")
    res = safe_json(r)

    if not res.get("success"):
        return await update.message.reply_text("❌ Error.")

    txt = "📁 **Files:**\n\n"
    for f in res["files"]:
        txt += f"• `{f['name']}` — {f['size_kb']} KB — {f['lines']} lines\n"

    await update.message.reply_text(txt, parse_mode="Markdown")


async def deletefile(update: Update, context):
    if not is_admin(update.message.from_user.id):
        return await update.message.reply_text("❌ Admin only.")
    if len(context.args) < 1:
        return await update.message.reply_text("Usage: /deletefile filename.txt")

    filename = context.args[0]

    r = requests.post(API_URL + "/api/bot/deletefile",
        json={"password": ADMIN_PASSWORD, "filename": filename}
    )
    res = safe_json(r)

    if res.get("success"):
        await update.message.reply_text(f"🗑 Deleted `{filename}`")
    else:
        await update.message.reply_text(f"❌ {res.get('error')}")


# ---------------------------------------------------
# MAIN
# ---------------------------------------------------
def main():
    TOKEN = "YOUR_BOT_TOKEN_HERE"

    app = ApplicationBuilder()\
        .token(TOKEN)\
        .allowed_updates(["message", "my_chat_member", "chat_member"])\
        .build()

    admin_conv = ConversationHandler(
        entry_points=[CommandHandler("admin", admin_panel)],
        states={ASK_PASS: [MessageHandler(filters.TEXT, admin_password)]},
        fallbacks=[]
    )
    app.add_handler(admin_conv)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addkey", add_key))
    app.add_handler(CommandHandler("delkey", delete_key))
    app.add_handler(CommandHandler("check", check_key))
    app.add_handler(CommandHandler("checkinfo", check_info))
    app.add_handler(CommandHandler("extend", extend_key))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("genkey", genkey))
    app.add_handler(CommandHandler("addaccess", addaccess))

    app.add_handler(CommandHandler("addfile", addfile))
    app.add_handler(CommandHandler("listfiles", listfiles))
    app.add_handler(CommandHandler("deletefile", deletefile))

    app.add_handler(MessageHandler(filters.Document.ALL, file_receiver))

    # admin tracking FIXED
    app.add_handler(ChatMemberHandler(track_bot_status, ChatMemberHandler.MY_CHAT_MEMBER))

    print("🤖 Bot Running…")
    app.run_polling()


if __name__ == "__main__":
    main()
