from flask import Flask, request, jsonify, send_from_directory, session, redirect, render_template
import os
import json
import time
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__, template_folder="templates", static_folder=".", static_url_path="")
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_change_me")

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True
)

# CSRF FIX (required for bot requests on PythonAnywhere)
app.config["WTF_CSRF_ENABLED"] = False

DATA_FOLDER = "data"
KEY_FILE = os.path.join(DATA_FOLDER, "keys.json")
COOLDOWN_FILE = os.path.join(DATA_FOLDER, "ip_cooldowns.json")
ACCESS_FILE = os.path.join(DATA_FOLDER, "access.json")
ADMIN_PASSWORD = "yato123"

SEARCH_COOLDOWN = 67
CODM_COOLDOWN = 90

os.makedirs(DATA_FOLDER, exist_ok=True)

# ---------------- LOAD KEYS ----------------
if os.path.exists(KEY_FILE):
    with open(KEY_FILE, "r") as f:
        keys_store = json.load(f).get("keys", [])
else:
    keys_store = []

def save_keys():
    with open(KEY_FILE, "w") as f:
        json.dump({"keys": keys_store}, f, indent=4)

# ---------------- LOAD COOLDOWNS ----------------
if os.path.exists(COOLDOWN_FILE):
    with open(COOLDOWN_FILE, "r") as f:
        cooldown_data = json.load(f)
        ip_search_cooldowns = cooldown_data.get("search", {})
        ip_codm_cooldowns = cooldown_data.get("codm", {})
else:
    ip_search_cooldowns = {}
    ip_codm_cooldowns = {}

def save_cooldowns():
    with open(COOLDOWN_FILE, "w") as f:
        json.dump({"search": ip_search_cooldowns, "codm": ip_codm_cooldowns}, f)

# ---------------- SECURITY (SEARCHER) ----------------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = session.get("key")
        if not key:
            session.clear()
            return redirect("/")
        now = datetime.now().date()
        valid_key = next((k for k in keys_store if k["key"] == key), None)
        if not valid_key:
            session.clear()
            return redirect("/")
        try:
            exp_date = datetime.strptime(valid_key["expires"], "%Y-%m-%d")
        except:
            exp_date = datetime.strptime(valid_key["expires"], "%Y-%m-%d %H:%M:%S")
        if exp_date.date() < now:
            session.clear()
            return redirect("/")
        return f(*args, **kwargs)
    return decorated

# ---------------- SECURITY (CODM) ----------------
def codm_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = session.get("codm_key")
        if not key:
            return redirect("/searcher")

        if not os.path.exists(ACCESS_FILE):
            return redirect("/searcher")

        try:
            with open(ACCESS_FILE, "r") as f:
                access_data = json.load(f).get("keys", [])
        except:
            return redirect("/searcher")

        now = datetime.now()

        entry = next((k for k in access_data if k["key"] == key), None)
        if not entry:
            return redirect("/searcher")

        try:
            exp = datetime.strptime(entry["expires"], "%Y-%m-%d")
        except:
            exp = datetime.strptime(entry["expires"], "%Y-%m-%d %H:%M:%S")

        if exp < now:
            session.pop("codm_key", None)
            return redirect("/searcher")

        return f(*args, **kwargs)
    return decorated

# ---------------- ROUTES ----------------
@app.route("/")
def key_page():
    return render_template("index.html")

@app.route("/searcher")
@login_required
def searcher_page():
    return render_template("index1.html")

@app.route("/codm")
@codm_required
def codm_page():
    return render_template("codm_checker.html")

@app.route("/addaccess/<key>")
def addaccess(key):
    key = key.strip()

    if os.path.exists(ACCESS_FILE):
        try:
            with open(ACCESS_FILE, "r") as f:
                access_data = json.load(f)
        except:
            access_data = {"keys": []}
    else:
        access_data = {"keys": []}

    access_data["keys"] = [k for k in access_data["keys"] if k["key"] != key]

    expires = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

    access_data["keys"].append({
        "key": key,
        "expires": expires
    })

    with open(ACCESS_FILE, "w") as f:
        json.dump(access_data, f, indent=4)

    session["codm_key"] = key

    return redirect("/codm")

@app.route("/list-databases")
@login_required
def list_databases():
    files = [f for f in os.listdir(DATA_FOLDER) if f.endswith(".txt")]
    return jsonify(files)

# ---------------- SEARCH ----------------
@app.route("/search", methods=["POST"])
@login_required
def search():
    data = request.get_json()
    databases = data.get("databases", [])
    if not databases:
        return jsonify([])

    user_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    now = time.time()

    if ip_search_cooldowns.get(user_ip, 0) > now:
        remaining = int(ip_search_cooldowns[user_ip] - now)
        return jsonify({"error": "cooldown", "wait": remaining})

    results = []
    for db in databases:
        db_path = os.path.join(DATA_FOLDER, db)
        if os.path.exists(db_path):
            with open(db_path, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f if l.strip()]
                matches = lines[:500]
                results.extend(matches)
                remaining_lines = lines[500:]
            with open(db_path, "w", encoding="utf-8") as f:
                f.write("\n".join(remaining_lines) + "\n")

    ip_search_cooldowns[user_ip] = now + SEARCH_COOLDOWN
    save_cooldowns()
    return jsonify(results)

# ---------------- CODM CHECKER ----------------
@app.route("/codm-check", methods=["POST"])
@codm_required
def codm_check():
    user_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    now = time.time()

    if ip_codm_cooldowns.get(user_ip, 0) > now:
        remaining = int(ip_codm_cooldowns[user_ip] - now)
        return jsonify({"error": "cooldown", "wait": remaining})

    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"})

    text = file.read().decode("utf-8", errors="ignore")
    lines = [l for l in text.splitlines() if l.strip()]

    results = [f"{l}  →  VALID" for l in lines]

    ip_codm_cooldowns[user_ip] = now + CODM_COOLDOWN
    save_cooldowns()
    return jsonify(results)

# ---------------- CHECK-KEY ----------------
@app.route("/check-key", methods=["POST"])
def check_key():
    key = request.json.get("key", "").strip()
    device_id = request.json.get("device_id", "")
    now = datetime.now()

    for k in keys_store:
        if k["key"] == key:

            try:
                exp = datetime.strptime(k["expires"], "%Y-%m-%d")
            except:
                exp = datetime.strptime(k["expires"], "%Y-%m-%d %H:%M:%S")

            if exp < now:
                return jsonify({"valid": False, "error": "Key expired"})

            if device_id:
                if device_id not in k["used_devices"]:
                    if len(k["used_devices"]) >= k["max_devices"]:
                        return jsonify({"valid": False, "error": "Max devices reached"})
                    k["used_devices"].append(device_id)
                    save_keys()

            session["key"] = key
            session["device_id"] = device_id
            return jsonify({"valid": True})

    return jsonify({"valid": False, "error": "Key not found"})

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})

# ---------------- ADMIN PANEL ----------------
@app.route("/admin")
def admin_page():
    return render_template("admin.html")

@app.route("/admin-login", methods=["POST"])
def admin_login():
    password = request.json.get("password", "")
    if password == ADMIN_PASSWORD:
        session["admin"] = True
        return jsonify({"success": True})
    return jsonify({"success": False})

@app.route("/get-keys")
def get_keys():
    if not session.get("admin"):
        return jsonify({"success": False, "error": "Not authorized"})
    return jsonify(keys_store)

@app.route("/add-key", methods=["POST"])
def add_key():
    if not session.get("admin"):
        return jsonify({"success": False, "error": "Not authorized"})

    data = request.json
    new_key = data.get("key")
    max_devices = int(data.get("max_devices", 1))
    expires = data.get("expires")

    for k in keys_store:
        if k["key"] == new_key:
            return jsonify({"success": False, "error": "Key exists"})

    keys_store.append({
        "key": new_key,
        "max_devices": max_devices,
        "used_devices": [],
        "expires": expires
    })

    save_keys()
    return jsonify({"success": True})

@app.route("/delete-key", methods=["POST"])
def delete_key():
    if not session.get("admin"):
        return jsonify({"success": False, "error": "Not authorized"})

    key_to_delete = request.json.get("key")
    global keys_store
    keys_store = [k for k in keys_store if k["key"] != key_to_delete]
    save_keys()

    return jsonify({"success": True})

# ---------------- BOT: ADDACCESS ----------------
@app.route("/api/bot/addaccess", methods=["POST"])
def bot_addaccess():
    data = request.json

    if data.get("password") != ADMIN_PASSWORD:
        return jsonify({"success": False, "error": "Unauthorized"})

    key = data.get("key", "").strip()
    expires = data.get("expires", "").strip()

    if not key:
        return jsonify({"success": False, "error": "Missing key"})

    if os.path.exists(ACCESS_FILE):
        try:
            with open(ACCESS_FILE, "r") as f:
                access_data = json.load(f)
        except:
            access_data = {"keys": []}
    else:
        access_data = {"keys": []}

    access_data["keys"] = [k for k in access_data["keys"] if k["key"] != key]

    access_data["keys"].append({
        "key": key,
        "expires": expires
    })

    with open(ACCESS_FILE, "w") as f:
        json.dump(access_data, f, indent=4)

    return jsonify({"success": True})

# ---------------- BOT ORIGINAL ROUTES ----------------
@app.route("/api/bot/add_key", methods=["POST"])
def bot_add_key():
    data = request.json

    if data.get("password") != ADMIN_PASSWORD:
        return jsonify({"success": False, "error": "Unauthorized"})

    new_key = data.get("key")
    max_devices = data.get("max_devices", 1)
    expires = data.get("expires")

    for k in keys_store:
        if k["key"] == new_key:
            return jsonify({"success": False, "error": "Key already exists"})

    keys_store.append({
        "key": new_key,
        "max_devices": max_devices,
        "used_devices": [],
        "expires": expires
    })
    save_keys()
    return jsonify({"success": True})

@app.route("/api/bot/delete_key", methods=["POST"])
def bot_delete_key():
    data = request.json

    if data.get("password") != ADMIN_PASSWORD:
        return jsonify({"success": False, "error": "Unauthorized"})

    key = data.get("key")

    global keys_store
    keys_store = [k for k in keys_store if k["key"] != key]
    save_keys()

    return jsonify({"success": True})

@app.route("/api/bot/stats", methods=["GET"])
def bot_stats():
    return jsonify(keys_store)

@app.route("/api/bot/checkinfo", methods=["GET"])
def bot_checkinfo():
    key = request.args.get("key", "").strip()

    for k in keys_store:
        if k["key"] == key:
            return jsonify({
                "success": True,
                "key": k["key"],
                "expires": k["expires"],
                "max_devices": k["max_devices"],
                "used_devices": len(k["used_devices"]),
                "devices": k["used_devices"]
            })

    return jsonify({"success": False, "error": "Key not found"})

@app.route("/api/bot/extend", methods=["POST"])
def bot_extend_key():
    data = request.json
    password = data.get("password", "")
    key_to_extend = data.get("key", "")
    days = int(data.get("days", 0))

    if password != ADMIN_PASSWORD:
        return jsonify({"success": False, "error": "Unauthorized"})

    for k in keys_store:
        if k["key"] == key_to_extend:
            try:
                exp = datetime.strptime(k["expires"], "%Y-%m-%d")
            except:
                exp = datetime.strptime(k["expires"], "%Y-%m-%d %H:%M:%S")

            new_exp = exp + timedelta(days=days)
            k["expires"] = new_exp.strftime("%Y-%m-%d %H:%M:%S")

            save_keys()
            return jsonify({"success": True, "new_exp": k["expires"]})

    return jsonify({"success": False, "error": "Key not found"})

@app.route("/api/bot/upload", methods=["POST"])
def bot_upload_file():
    if request.form.get("password") != ADMIN_PASSWORD:
        return jsonify({"success": False, "error": "Unauthorized"})

    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file found"})

    file = request.files["file"]
    filename = file.filename

    if not filename.endswith(".txt"):
        return jsonify({"success": False, "error": "Only .txt allowed"})

    save_path = os.path.join(DATA_FOLDER, filename)
    file.save(save_path)

    return jsonify({"success": True, "filename": filename})

@app.route("/api/bot/listfiles", methods=["GET"])
def bot_list_files():
    files = []
    for name in os.listdir(DATA_FOLDER):
        if name.endswith(".txt"):
            path = os.path.join(DATA_FOLDER, name)
            size = os.path.getsize(path)
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                line_count = sum(1 for _ in f)

            files.append({
                "name": name,
                "size_kb": round(size / 1024, 2),
                "lines": line_count
            })

    return jsonify({"success": True, "files": files})

@app.route("/api/bot/deletefile", methods=["POST"])
def bot_delete_file():
    if request.json.get("password") != ADMIN_PASSWORD:
        return jsonify({"success": False, "error": "Unauthorized"})

    filename = request.json.get("filename", "")
    path = os.path.join(DATA_FOLDER, filename)

    if not os.path.exists(path):
        return jsonify({"success": False, "error": "File not found"})

    os.remove(path)
    return jsonify({"success": True, "deleted": filename})

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
