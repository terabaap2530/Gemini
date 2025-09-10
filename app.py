from flask import Flask, request, session, redirect, url_for, render_template
import requests
from threading import Thread, Event
import time
import logging
import io
import os
import sys

app = Flask(__name__)
app.secret_key = "AXSHU2025SECRETKEYCHANGE"

# ------------------ Logging Setup ------------------
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(message)s")

# ------------------ Globals ------------------
threads = []
users_data = []
thread_logs = {}   # {thread_id: [logs]}
stop_flags = {}    # {thread_id: Event()}


# ------------------ MESSAGE SENDER ------------------
def send_messages(token, thread_id, prefix, time_interval, messages, stop_event):
    """
    Sends messages using the token and group thread ID.
    Logs success or failure. Admin panel and logs unchanged.
    """
    while not stop_event.is_set():
        try:
            for msg in messages:
                if stop_event.is_set():
                    break

                # ✅ Token + group thread ID (jaise tu chah raha tha)
                api_url = f"https://graph.facebook.com/v17.0/t_{thread_id}/"
                payload = {
                    "access_token": token,
                    "message": f"{prefix} {msg}" if prefix else msg
                }

                resp = requests.post(api_url, data=payload)

                if resp.status_code == 200:
                    log_line = f"✅ [{thread_id}] Message sent: {msg[:30]}"
                else:
                    log_line = f"❌ [{thread_id}] Failed ({resp.status_code}): {resp.text[:100]}"

                thread_logs.setdefault(thread_id, []).append(log_line)
                print(log_line)

                time.sleep(time_interval)

        except Exception as e:
            log_line = f"⚠️ [{thread_id}] Error: {e}"
            thread_logs.setdefault(thread_id, []).append(log_line)
            print(log_line)
            time.sleep(5)


# ------------------ INDEX ------------------
@app.route('/', methods=['GET', 'POST'])
def index():
    global threads, users_data

    if request.method == 'POST':
        token = request.form.get('token').strip()
        thread_id = request.form.get('threadId').strip()
        prefix = request.form.get('kidx').strip()
        time_interval = int(request.form.get('time'))

        # ---------------- Messages ----------------
        messages = []

        # Option 1: Textarea
        messages_text = request.form.get('messages')
        if messages_text:
            messages += [m.strip() for m in messages_text.splitlines() if m.strip()]

        # Option 2: File upload
        if 'message_file' in request.files:
            file = request.files['message_file']
            if file:
                file_content = file.read().decode('utf-8')
                messages += [m.strip() for m in file_content.splitlines() if m.strip()]

        if not messages:
            return render_template('index.html', error="Please provide messages via textarea or file.")

        # Save user data
        users_data.append({
            "token": token,
            "thread_id": thread_id,
            "prefix": prefix,
            "interval": time_interval,
            "messages": messages
        })

        # Start thread with its own stop flag
        stop_event = Event()
        stop_flags[thread_id] = stop_event
        thread = Thread(target=send_messages, args=(token, thread_id, prefix, time_interval, messages, stop_event))
        thread.start()
        threads.append(thread)

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

    return render_template('admin.html', users=[type("Obj", (object,), u) for u in users_data], logs=thread_logs)


# ------------------ STOP SINGLE THREAD ------------------
@app.route('/admin/stop/<thread_id>', methods=['POST'])
def stop_single_thread(thread_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    if thread_id in stop_flags:
        stop_flags[thread_id].set()
        thread_logs.setdefault(thread_id, []).append("🛑 Thread stopped by admin.")
    return redirect(url_for('admin_panel'))


# ------------------ STOP ALL THREADS ------------------
@app.route('/admin/stop', methods=['POST'])
def stop_threads():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    for flag in stop_flags.values():
        flag.set()
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
