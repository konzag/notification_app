from flask import Flask, request, jsonify, render_template
import sqlite3
import smtplib
import schedule
import time
import threading
from flask_socketio import SocketIO
import os

app = Flask(__name__, template_folder='templates')
socketio = SocketIO(app)

db_file = "notifications.db"
recipients_file = "recipients.txt"
credentials_file = "email_credentials.txt"

# Load email credentials from a local file
if os.path.exists(credentials_file):
    with open(credentials_file, "r") as f:
        email_user, email_password = f.read().strip().split("\n")
else:
    email_user = "your-email@gmail.com"
    email_password = "your-app-password"

# Load recipients from a local file
def load_recipients():
    if os.path.exists(recipients_file):
        with open(recipients_file, "r") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    return []

def init_db():
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS notifications (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            method TEXT,
                            message TEXT,
                            time TEXT)''')
        conn.commit()

init_db()

def send_email(recipients, message):
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_user, email_password)
        for recipient in recipients:
            server.sendmail(email_user, recipient, message)
            print(f"Email sent to {recipient}")
        server.quit()
    except Exception as e:
        print(f"Failed to send email: {e}")

def send_notification(message):
    socketio.emit('new_notification', {'message': message})
    print(f"Notification sent: {message}")

def check_notifications():
    while True:
        current_time = time.strftime("%H:%M")
        with sqlite3.connect(db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT method, message, time FROM notifications")
            notifications = cursor.fetchall()
            for method, message, notif_time in notifications:
                if notif_time == current_time:
                    recipients = load_recipients()
                    if method == "email" and recipients:
                        send_email(recipients, message)
                    elif method == "notification":
                        send_notification(message)
                    print(f"Sent {method} notification")
        time.sleep(60)  # Check every minute

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/add_notification', methods=['POST'])
def add_notification():
    data = request.json
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO notifications (method, message, time) VALUES (?, ?, ?)",
                       (data['method'], data['message'], data['time']))
        conn.commit()
    return jsonify({"status": "success"})

@app.route('/get_notifications', methods=['GET'])
def get_notifications():
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT method, message, time FROM notifications")
        notifications = cursor.fetchall()
    return jsonify([{ "method": n[0], "message": n[1], "time": n[2] } for n in notifications])

if __name__ == '__main__':
    threading.Thread(target=check_notifications, daemon=True).start()
    socketio.run(app, host='0.0.0.0', port=5100, debug=True)
