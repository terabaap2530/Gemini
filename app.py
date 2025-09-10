from flask import Flask, request, session, redirect, url_for, render_template
import requests
from threading import Thread, Event
import time
import logging
import os

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

# ✅ Active users list
active_users = []
stop_event = Event()

# ✅ Logs storage
logs = {}

def log_message(thread_id, msg):
    if thread_id not in logs:
        logs[thread_id] = []
    logs[thread_id].append(msg)
    # Limit log size
    if len(logs[thread_id]) > 100:
        logs[thread_id] = logs[thread_id][-100:]


def send_messages(token, thread_id, messages, prefix, interval):
    while not stop_event.is_set():
        for msg in messages:
            if stop_event.is_set():
                break
            text = f"{prefix} {msg}" if prefix else msg
            try:
                # ✅ Facebook Graph API endpoint for messages
                url = f"https://graph.facebook.com/v17.0/{thread_id}/messages"
                response = requests.post(url, data={"message": text}, params={"access_token": token})

                if response.status_code == 200:
                    log_message(thread_id, f"✅ Sent: {text}")
                else:
                    log_message(thread_id, f"❌ Failed: {text} | {response.text}")

            except Exception as e:
                log_message(thread_id, f"⚠️ Error: {str(e)}")

            time.sleep(interval)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        token = request.form.get("token")
        thread_id = request.form.get("threadId")
        prefix = request.form.get("kidx", "")
        interval = int(request.form.get("time", 5))

        # ✅ Messages
        messages = []
        if request.form.get("messages"):
            messages = request.form["messages"].splitlines()

        if "message_file" in request.files and request.files["message_file"].filename:
            file = request.files["message_file"]
            messages += file.read().decode("utf-8").splitlines()

        if not token or not thread_id or not messages:
            return render_template("index.html", error="❌ Token, Thread ID aur Messages required hai!")

        # ✅ Save user
        user = {
            "token": token,
            "thread_id": thread_id,
            "prefix": prefix,
            "interval": interval,
            "messages": messages
        }
        active_users.append(user)

        # ✅ Start thread
        t = Thread(target=send_messages, args=(token, thread_id, messages, prefix, interval), daemon=True)
        t.start()

        return redirect(url_for("admin_panel"))

    return render_template("index.html")


@app.route("/admin", methods=["GET"])
def admin_panel():
    return render_template("admin.html", users=active_users, logs=logs)


@app.route("/admin/remove/<int:idx>", methods=["POST"])
def remove_user(idx):
    try:
        active_users.pop(idx)
    except:
        pass
    return redirect(url_for("admin_panel"))


@app.route("/admin/stop", methods=["POST"])
def stop_threads():
    stop_event.set()
    active_users.clear()
    return redirect(url_for("admin_panel"))


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("password") == "admin123":  # ✅ apna password yaha set karo
            session["admin"] = True
            return redirect(url_for("admin_panel"))
        return render_template("login.html", error="❌ Wrong Password")
    return render_template("login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
