import os
import cv2
import pyttsx3
import logging
import hashlib
import pandas as pd
import smtplib
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, Response
from deepface import DeepFace
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import shutil
import webbrowser
import threading

app = Flask(__name__)
app.secret_key = "supersecretkey"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

HOST_IP = "localhost"

CAPTURED_FACE_PATH = "Captured_faces/captured_image.jpg"
ALLOWED_FACES_DIR = "Allowed_faces/"
EXCEL_FILE = "tracking_log.xlsx" 

OWNER_EMAIL = "your_owner_email@example.com"
SENDER_EMAIL = "your_sender_email@example.com"
SENDER_PASSWORD = "your_app_password"

os.makedirs(os.path.dirname(CAPTURED_FACE_PATH), exist_ok=True)
os.makedirs(ALLOWED_FACES_DIR, exist_ok=True)

ALLOWED_FACES_MAPPING = {
    "Allowed_faces/allowed_person_1.jpg": "John Doe",
    "Allowed_faces/allowed_person_2.jpg":"ian somerhalder"
}

def speak(text):
    try:
        local_engine = pyttsx3.init()
        local_engine.say(text)
        local_engine.runAndWait()
        local_engine.stop()
    except Exception as e:
        logging.error(f"❌ Voice error: {e}")

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

stored_password_hash = hash_password("1234")
attempts = 3
log_password_hash = hash_password("admin123")

def capture_face():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        logging.error("❌ Error: Could not access the camera.")
        return None
    for _ in range(5):
        ret, frame = cap.read()
    ret, frame = cap.read()
    cap.release()
    if ret:
        cv2.imwrite(CAPTURED_FACE_PATH, frame)
        logging.info("✅ Image captured successfully.")
        return CAPTURED_FACE_PATH
    else:
        logging.error("❌ Error: Could not capture image.")
        return None

def gen_frames():
    cap = cv2.VideoCapture(0)
    while True:
        success, frame = cap.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

def send_email_alert(image_path, alert_type="stranger"):
    try:
        approve_link = f"http://{HOST_IP}:5000/approve"
        deny_link = f"http://{HOST_IP}:5000/deny"
        html_content = render_template("mail_template.html", approve_link=approve_link, deny_link=deny_link, alert_type=alert_type)

        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = OWNER_EMAIL
        msg['Subject'] = "🚨 ALERT: Multiple Failed Password Attempts" if alert_type == "attempts" else "🚪 Access Request: Unknown Person at Your Door"

        msg.attach(MIMEText(html_content, 'html'))
        with open(image_path, 'rb') as img:
            mime_img = MIMEImage(img.read(), _subtype="jpeg")
            mime_img.add_header('Content-ID', '<image1>')
            msg.attach(mime_img)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)

        logging.info("✅ Email sent successfully.")
    except Exception as e:
        logging.error(f"❌ Email sending failed: {e}")

def send_entry_alert(image_path, person_name):
    try:
        mark_unknown_link = f"http://{HOST_IP}:5000/mark-unknown"
        html_content = render_template("mail_template_recognized.html", person_name=person_name, mark_unknown_link=mark_unknown_link)

        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = OWNER_EMAIL
        msg['Subject'] = f"✅ {person_name.title()} just unlocked the door."

        msg.attach(MIMEText(html_content, 'html'))
        with open(image_path, 'rb') as img:
            mime_img = MIMEImage(img.read(), _subtype="jpeg")
            mime_img.add_header('Content-ID', '<image1>')
            msg.attach(mime_img)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)

        logging.info(f"📩 Entry alert sent for {person_name}.")
    except Exception as e:
        logging.error(f"❌ Failed to send entry alert: {e}")

def recognize_face():
    captured_face = capture_face()
    if not captured_face:
        return "Error", "Unknown", 0.0

    try:
        result_df = DeepFace.find(img_path=captured_face, db_path=ALLOWED_FACES_DIR, enforce_detection=True)
        if result_df and not result_df[0].empty:
            best_match = result_df[0].iloc[0]
            matched_path = best_match["identity"]
            distance = best_match["distance"]
            confidence = (1 - distance) * 100
            name = ALLOWED_FACES_MAPPING.get(matched_path, "Unknown")

            logging.info(f"✅ Match found: {name} (Distance: {distance:.4f}, Confidence: {confidence:.2f}%)")
            send_entry_alert(captured_face, name)
            return "Allowed", name, confidence
        else:
            logging.info("🚫 No match found. Stranger detected.")
            send_email_alert(captured_face)
            return "Denied", "Unknown", 0.0
    except Exception as e:
        logging.error(f"Face recognition failed: {e}")
        return "Error", "Unknown", 0.0

def log_entry(person_name, password_status, face_status, door_status, device_name, confidence_score):
    data = {
        "Person": [person_name],
        "Date": [datetime.now().strftime("%Y-%m-%d")],
        "Time": [datetime.now().strftime("%H:%M:%S")],
        "Password Status": [password_status],
        "Face Recognition Status": [face_status],
        "Door Opened": [door_status],
        "Device": [device_name],
        "Confidence Score": [f"{confidence_score:.2f}%"]
    }
    df = pd.DataFrame(data)
    if os.path.exists(EXCEL_FILE):
        existing_df = pd.read_excel(EXCEL_FILE)
        df = pd.concat([existing_df, df], ignore_index=True)
    df.to_excel(EXCEL_FILE, index=False)

@app.route('/', methods=['GET', 'POST'])
def home():
    global attempts
    if request.method == 'POST':
        password = request.form.get('password')
        if hash_password(password) == stored_password_hash:
            flash("✅ Password Correct! Proceeding to Face Recognition...", "success")
            return redirect(url_for('face_recognition', device_name="Main Door"))
        attempts -= 1
        if attempts > 0:
            flash(f"❌ Wrong Password! {attempts} attempts left.", "warning")
        else:
            flash("🚨 Access Denied! Too many failed attempts.", "danger")
            capture_face()
            send_email_alert(CAPTURED_FACE_PATH, alert_type="attempts")
            log_entry("Unknown", "Incorrect (3 times)", "Not Attempted", "No", "Main Door", 0.0)
            attempts = 3
        return redirect(url_for('home'))
    return render_template('index.html')

@app.route('/approve')
def approve():
    person_name = "Unknown"
    speak("Owner granted access. Welcome!")
    log_entry(person_name, "Not Attempted", "Stranger", "Yes", "Remote Approval", 0.0)
    flash("✅ Stranger Approved by Owner", "success")
    return redirect(url_for("home"))

@app.route('/deny')
def deny():
    person_name = "Unknown"
    speak("Owner denied access.")
    log_entry(person_name, "Not Attempted", "Stranger", "No", "Remote Denial", 0.0)
    flash("🚫 Stranger Denied by Owner", "danger")
    return redirect(url_for("home"))

@app.route('/allow-once')
def allow_once():
    person_name = "Unknown"
    speak("Temporary access granted by owner.")
    log_entry(person_name, "Not Attempted", "Stranger", "Yes (Temp)", "Remote Temporary Approval", 0.0)
    flash("⏳ Temporary Access Granted", "info")
    return redirect(url_for("home"))

@app.route('/mark-unknown')
def mark_unknown():
    person_name = "Previously Recognized"
    speak("This person is now marked as unknown.")
    log_entry(person_name, "N/A", "Changed to Unknown", "N/A", "Admin Action", 0.0)
    flash("🤔 Marked as Unknown", "warning")
    return redirect(url_for("home"))

@app.route("/face-recognition/<device_name>")
def face_recognition(device_name):
    status, person_name, confidence_score = recognize_face()
    door_status = "Yes" if status == "Allowed" else "No"
    log_entry(person_name, "Correct", status, door_status, device_name, confidence_score)

    if status == "Allowed":
        message = f"Welcome, {person_name}!"
        flash(f"✅ Access Granted! Welcome {person_name}. Confidence: {confidence_score:.2f}%", "success")
    elif status == "Error":
        message = "Camera Error!"
        flash("❌ Camera error. Could not access the webcam.", "danger")
    else:
        message = "Access Denied!"
        flash(f"🚨 Access Denied! Confidence: {confidence_score:.2f}%. Email sent to owner.", "danger")

    try:
        speak(message)
    except Exception as e:
        logging.error(f"❌ Voice feedback error: {e}")

    return redirect(url_for("home"))

@app.route('/live')
def live():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/live', methods=['GET'])
def live_feed():
    token = request.args.get('token')
    if token == 'secure123':
        return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
    return "Unauthorized", 403

@app.route("/log-password", methods=["GET", "POST"])
def log_password():
    if request.method == "POST":
        password = request.form["password"]
        if hash_password(password) == log_password_hash:
            session["logged_in"] = True
            return redirect(url_for("view_logs"))
        else:
            flash("❌ Incorrect password!", "danger")
    return render_template("log_password.html")

@app.route("/view-logs", methods=["GET"])
def view_logs():
    logs = []
    if os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE)
        person = request.args.get("person", "").strip().lower()
        date = request.args.get("date", "")
        password_status = request.args.get("password_status", "")
        face_status = request.args.get("face_status", "")
        door_opened = request.args.get("door_opened", "")
        if person:
            df = df[df["Person"].str.lower().str.contains(person)]
        if date:
            df = df[df["Date"] == date]
        if password_status:
            df = df[df["Password Status"] == password_status]
        if face_status:
            df = df[df["Face Recognition Status"] == face_status]
        if door_opened:
            df = df[df["Door Opened"] == "Yes"]
        logs = df.to_dict(orient="records")
    return render_template("view_logs.html", logs=logs)

def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000/")

if __name__ == "__main__":
    threading.Timer(1.25, open_browser).start()
    app.run(debug=True)
