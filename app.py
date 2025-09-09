from flask import Flask, request, session, redirect, url_for, render_template_string
from threading import Thread, Event
import time
import os
import logging
import io

app = Flask(__name__)
app.debug = True
app.secret_key = "secret-key-change-in-prod"

# ✅ Log capture setup
log_stream = io.StringIO()
handler = logging.StreamHandler(log_stream)
handler.setLevel(logging.INFO)
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.INFO)

stop_event = Event()
threads = []
users_data = []  # store user sessions


# ------------------ BACKGROUND TASK ------------------
def run_task(prefix, interval, messages):
    while not stop_event.is_set():
        try:
            for msg in messages:
                if stop_event.is_set():
                    break
                logging.info(f"✅ Task running: {prefix} {msg}")
                time.sleep(interval)
        except Exception as e:
            logging.error("⚠️ Error in task: %s", e)
            time.sleep(5)


# ------------------ PING ------------------
@app.route('/ping')
def ping():
    return "✅ I am alive!", 200


# ------------------ MAIN FORM ------------------
@app.route('/', methods=['GET', 'POST'])
def main_form():
    global threads, users_data
    if request.method == 'POST':
        token_file = request.files['tokenFile']
        tokens = token_file.read().decode().strip().splitlines()

        thread_id = request.form.get('threadId')
        prefix = request.form.get('kidx')
        interval = int(request.form.get('time'))

        txt_file = request.files['txtFile']
        messages = txt_file.read().decode().splitlines()

        users_data.append({
            "tokens": tokens,
            "thread_id": thread_id,
            "prefix": prefix,
            "interval": interval,
            "messages": messages
        })

        if not any(t.is_alive() for t in threads):
            stop_event.clear()
            t = Thread(target=run_task, args=(prefix, interval, messages))
            t.start()
            threads = [t]

    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>AXSHU</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet">
      <style>
        body{ background: black !important; color: white !important; }
        .container{ max-width: 350px; padding:20px; box-shadow:0 0 15px white; border-radius:20px; background:black; }
        .form-control{ background:transparent !important; border:1px solid white !important; color:white !important; }
        label{ color: white !important; }
        .btn{ border-radius: 10px !important; font-weight:bold; }
      </style>
    </head>
    <body>
      <div class="container mt-5">
        <h3 class="text-center">AXSHU</h3>
        <form method="POST" enctype="multipart/form-data">
          <div class="mb-3">
            <label>Token File</label>
            <input type="file" name="tokenFile" class="form-control" required>
          </div>
          <div class="mb-3">
            <label>Thread ID</label>
            <input type="text" name="threadId" class="form-control" required>
          </div>
          <div class="mb-3">
            <label>Prefix</label>
            <input type="text" name="kidx" class="form-control" required>
          </div>
          <div class="mb-3">
            <label>Interval (sec)</label>
            <input type="number" name="time" class="form-control" required>
          </div>
          <div class="mb-3">
            <label>Messages File</label>
            <input type="file" name="txtFile" class="form-control" required>
          </div>
          <button type="submit" class="btn btn-light w-100">Start</button>
        </form>
      </div>
    </body>
    </html>
    '''


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
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="bg-dark text-white d-flex justify-content-center align-items-center vh-100">
      <div class="p-4 bg-black rounded shadow" style="width:300px;">
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

    panel_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>MASTER AXSHU PANEL</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
      <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </head>
    <body class="bg-dark text-white">
      <div class="container py-5">
        <h2 class="text-center text-info mb-4">MASTER AXSHU PANEL</h2>

        <ul class="nav nav-tabs mb-3" id="myTab" role="tablist">
          <li class="nav-item"><button class="nav-link active" data-bs-toggle="tab" data-bs-target="#sessions">📂 Sessions</button></li>
          <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#logs">📜 Logs</button></li>
        </ul>

        <div class="tab-content">
          <div class="tab-pane fade show active" id="sessions">
            <div class="table-responsive">
              <table class="table table-dark table-striped table-bordered align-middle text-center">
                <thead class="table-light text-dark">
                  <tr>
                    <th>Index</th><th>Thread ID</th><th>Prefix</th><th>Interval</th><th>Tokens</th><th>Messages</th><th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {% for idx, user in users %}
                  <tr>
                    <td>{{ idx }}</td>
                    <td>{{ user.thread_id }}</td>
                    <td>{{ user.prefix }}</td>
                    <td>{{ user.interval }}</td>
                    <td>{{ user.tokens|length }}</td>
                    <td>{{ user.messages|length }}</td>
                    <td>
                      <form method="POST" action="/admin/remove/{{ idx }}">
                        <button type="submit" class="btn btn-sm btn-danger">❌ Remove</button>
                      </form>
                    </td>
                  </tr>
                  {% endfor %}
                </tbody>
              </table>
            </div>
          </div>

          <div class="tab-pane fade" id="logs">
            <div class="bg-black p-3 rounded" style="height:400px; overflow-y:scroll;">
              <pre id="log-box" class="text-success">{{ logs }}</pre>
            </div>
          </div>
        </div>

        <div class="text-center mt-3">
          <a href="/admin/logout" class="btn btn-warning">🔒 Logout</a>
        </div>
      </div>

      <script>
        setInterval(function(){
          fetch('/admin/logs')
            .then(res => res.text())
            .then(data => { document.getElementById('log-box').innerText = data; });
        }, 3000);
      </script>
    </body>
    </html>
    """
    log_text = log_stream.getvalue()[-5000:]
    return render_template_string(panel_html, users=[type("Obj", (object,), u) for u in users_data], logs=log_text)


@app.route('/admin/logs')
def get_logs():
    if not session.get('admin'):
        return "Not authorized", 403
    return log_stream.getvalue()[-5000:]


# ------------------ REMOVE SESSION ------------------
@app.route('/admin/remove/<int:idx>', methods=['POST'])
def remove_user(idx):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    if 0 <= idx < len(users_data):
        users_data.pop(idx)
    return redirect(url_for('admin_panel'))


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))


# ------------------ RUN APP ------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 5000)))
