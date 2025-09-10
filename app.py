from flask import Flask, request, session, redirect, url_for, render_template
import requests
from threading import Thread, Event
import time
import logging
import io
import os
from bs4 import BeautifulSoup

app = Flask(__name__)
app.secret_key = "AXSHU2025SECRETKEYCHANGE"

# ------------------ Globals ------------------
users_data = []   # [{thread_id, cookies, thread, stop_event, log_stream}]

# ------------------ Helper: UID → ThreadId ------------------
def get_thread_id_from_uid(session_req, uid):
    try:
        r = session_req.get(
            f"https://mbasic.facebook.com/messages/read/?fbid={uid}",
            headers={"User-Agent": "Mozilla/5.0"},
            allow_redirects=True
        )
        if "t_" in r.url:
            return r.url.split("/")[-1]

        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            if "t_" in a["href"]:
                return "t_" + a["href"].split("t_")[-1]
    except Exception as e:
        return None
    return None

# ------------------ MESSAGE SENDER ------------------
def send_messages(cookies, thread_id, messages, stop_event, log_stream):
    logger = logging.getLogger(thread_id)
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(log_stream)
    logger.addHandler(handler)

    session_req = requests.Session()
    session_req.cookies.update(cookies)

    # ---- fetch fb_dtsg / jazoest ----
    try:
        r = session_req.get("https://mbasic.facebook.com/messages", headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        fb_dtsg = soup.find("input", {"name": "fb_dtsg"})["value"]
        jazoest = soup.find("input", {"name": "jazoest"})["value"]
        logger.info("✅ Tokens fetched")
    except Exception as e:
        logger.error(f"❌ Failed to fetch tokens: {e}")
        return

    # ---- convert UID → threadId ----
    if not thread_id.startswith("t_"):
        real_thread = get_thread_id_from_uid(session_req, thread_id)
        if real_thread:
            logger.info(f"ℹ️ UID {thread_id} → ThreadId: {real_thread}")
            thread_id = real_thread
        else:
            logger.error(f"❌ UID {thread_id} ka threadId fetch nahi ho paya")
            return

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": f"https://mbasic.facebook.com/messages/read/?tid={thread_id}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    i = 0
    while not stop_event.is_set():
        try:
            for msg in messages:
                if stop_event.is_set():
                    break
                data = {
                    "fb_dtsg": fb_dtsg,
                    "jazoest": jazoest,
                    "body": msg,
                    "tids": thread_id,
                    "wwwupp": "C3",
                }
                resp = session_req.post("https://mbasic.facebook.com/messages/send/", data=data, headers=headers)

                i += 1
                if "message sent" in resp.text.lower():
                    logger.info(f"[{i}] ✅ Sent: {msg[:30]}")
                else:
                    logger.warning(f"[{i}] ⚠️ Status uncertain: {msg[:30]}")

                time.sleep(3)
        except Exception as e:
            logger.error(f"⚠️ Error: {e}")
            time.sleep(5)

# ------------------ MAIN FORM ------------------
@app.route('/', methods=['GET', 'POST'])
def index():
    global users_data
    if request.method == 'POST':
        # --- Cookies (copy paste tokens) ---
        cookies_raw = request.form.get('cookies')
        cookies = {item.split('=', 1)[0].strip(): item.split('=', 1)[1].strip()
                   for item in cookies_raw.split(';') if '=' in item}

        thread_id = request.form.get('threadId')

        # --- Messages (from file only) ---
        messages = []
        if 'message_file' in request.files:
            file = request.files['message_file']
            if file:
                file_content = file.read().decode('utf-8')
                messages += [m.strip() for m in file_content.splitlines() if m.strip()]

        if not messages:
            return render_template('index.html', error="❌ Upload a message file!")

        stop_event = Event()
        log_stream = io.StringIO()
        thread = Thread(target=send_messages, args=(cookies, thread_id, messages, stop_event, log_stream))
        thread.start()

        users_data.append({
            "thread_id": thread_id,
            "cookies": cookies,
            "thread": thread,
            "stop_event": stop_event,
            "log_stream": log_stream
        })

    return render_template('index.html')

# ------------------ ADMIN LOGIN ------------------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == "AXSHU2025":
            session['admin'] = True
            return redirect(url_for('admin_panel'))
    return '''
    <form method="POST">
      <input type="password" name="password" placeholder="Admin Password">
      <button type="submit">Login</button>
    </form>
    '''

# ------------------ ADMIN PANEL ------------------
@app.route('/admin/panel')
def admin_panel():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    return render_template('admin_panel.html', users=list(enumerate(users_data)))

@app.route('/admin/logs/<int:idx>')
def thread_logs(idx):
    if not session.get('admin'):
        return "Not authorized", 403
    if 0 <= idx < len(users_data):
        return f"<pre>{users_data[idx]['log_stream'].getvalue()}</pre>"
    return "Invalid thread index", 404

@app.route('/admin/stop/<int:idx>', methods=['POST'])
def stop_thread(idx):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    if 0 <= idx < len(users_data):
        users_data[idx]['stop_event'].set()
        return redirect(url_for('admin_panel'))
    return "Invalid index", 404

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))

# ------------------ RUN ------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 5000)))
