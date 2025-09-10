from flask import Flask, request, redirect, url_for, render_template, session
import requests
from threading import Thread, Event
import time

app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # change this

# Active users storage
active_users = []
logs = []

# ================== Helper Functions ==================
def add_log(msg):
    logs.append(msg)
    if len(logs) > 200:  # Limit logs
        logs.pop(0)

def parse_cookies(cookie_str):
    """Convert cookie string into dict"""
    cookies = {}
    for part in cookie_str.split(";"):
        if "=" in part:
            k, v = part.strip().split("=", 1)
            cookies[k] = v
    return cookies

def send_message(cookies, thread_id, message):
    try:
        url = "https://mbasic.facebook.com/messages/send/"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {"tids": thread_id, "body": message}
        res = requests.post(url, headers=headers, cookies=cookies, data=data)
        return res.status_code == 200
    except Exception as e:
        return False

def message_thread(user, stop_event):
    cookies = parse_cookies(user["cookies"])
    while not stop_event.is_set():
        for msg in user["messages"]:
            if stop_event.is_set():
                break
            text = f"{user['prefix']} {msg}" if user["prefix"] else msg
            success = send_message(cookies, user["thread_id"], text)
            add_log(f"[{user['thread_id']}] {text} => {'✅ Sent' if success else '❌ Fail'}")
            time.sleep(user["interval"])

# ================== Routes ==================
@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    if request.method == "POST":
        cookies = request.form.get("cookies")
        thread_id = request.form.get("threadId")
        prefix = request.form.get("kidx") or ""
        interval = int(request.form.get("time", 5))

        # Messages: from textarea or file
        messages = []
        if request.form.get("messages"):
            messages = request.form.get("messages").splitlines()
        elif "message_file" in request.files:
            f = request.files["message_file"]
            if f and f.filename.endswith(".txt"):
                messages = f.read().decode("utf-8").splitlines()

        if not cookies or not thread_id or not messages:
            error = "❌ Please fill all required fields"
        else:
            stop_event = Event()
            user = {
                "cookies": cookies,
                "thread_id": thread_id,
                "prefix": prefix,
                "interval": interval,
                "messages": messages,
                "stop_event": stop_event,
                "logs": []
            }
            t = Thread(target=message_thread, args=(user, stop_event))
            t.daemon = True
            t.start()
            active_users.append(user)
            add_log(f"🚀 Started thread for {thread_id}")
            return redirect(url_for("admin_panel"))

    return render_template("index.html", error=error)


# ================== Admin ==================
@app.route("/admin", methods=["GET"])
def admin_panel():
    return render_template("admin_panel.html", users=active_users, logs=logs)

@app.route("/remove/<int:idx>", methods=["POST"])
def remove_user(idx):
    if 0 <= idx < len(active_users):
        active_users[idx]["stop_event"].set()
        add_log(f"🛑 Stopped thread for {active_users[idx]['thread_id']}")
        active_users.pop(idx)
    return redirect(url_for("admin_panel"))

@app.route("/stop_all", methods=["POST"])
def stop_threads():
    for u in active_users:
        u["stop_event"].set()
    active_users.clear()
    add_log("🛑 Stopped all threads")
    return redirect(url_for("admin_panel"))

# ================== Run ==================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
