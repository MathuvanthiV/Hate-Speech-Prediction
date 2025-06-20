from flask import Flask, render_template, request, redirect, session, url_for, flash
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import torch
import torch.nn.functional as F

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Change this in production!

# Initialize SQLite DB
def init_db():
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        is_admin INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        text TEXT,
        hate_label TEXT,
        hate_conf REAL,
        emotion_label TEXT,
        emotion_conf REAL,
        suggestion TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    conn.commit()
    conn.close()

init_db()

# Load Models
hate_model_name = "Hate-speech-CNERG/bert-base-uncased-hatexplain"
hate_tokenizer = AutoTokenizer.from_pretrained(hate_model_name)
hate_model = AutoModelForSequenceClassification.from_pretrained(hate_model_name)
hate_labels = ["normal", "offensive", "hate"]

emotion_model_name = "j-hartmann/emotion-english-distilroberta-base"
emotion_tokenizer = AutoTokenizer.from_pretrained(emotion_model_name)
emotion_model = AutoModelForSequenceClassification.from_pretrained(emotion_model_name)
emotion_labels = ['anger', 'disgust', 'fear', 'joy', 'neutral', 'sadness', 'surprise']

# Rephrasing suggestions
def suggest_rephrasing(emotion):
    suggestions = {
        "anger": "Try expressing it calmly. E.g., 'I'm frustrated, but let's talk it through.'",
        "disgust": "Try rewording it more constructively. E.g., 'I find this unpleasant, let's improve it.'"
    }
    return suggestions.get(emotion.lower())

# Predict hate speech
def predict_hate(text):
    inputs = hate_tokenizer(text, return_tensors="pt", truncation=True, padding=True)
    outputs = hate_model(**inputs)
    probs = F.softmax(outputs.logits, dim=1)
    confidence, predicted_class = torch.max(probs, dim=1)
    label = hate_labels[predicted_class.item()]
    return label.capitalize(), round(confidence.item() * 100, 2)

# Predict emotion
def predict_emotion(text):
    inputs = emotion_tokenizer(text, return_tensors="pt", truncation=True, padding=True)
    outputs = emotion_model(**inputs)
    probs = F.softmax(outputs.logits, dim=1)
    confidence, predicted_class = torch.max(probs, dim=1)
    label = emotion_labels[predicted_class.item()]
    return label.capitalize(), round(confidence.item() * 100, 2)

# Home route
@app.route("/", methods=["GET", "POST"])
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))

    result = emotion = suggestion = None
    confidence = emotion_conf = None

    if request.method == "POST":
        text = request.form["text"]
        result, confidence = predict_hate(text)
        emotion, emotion_conf = predict_emotion(text)
        suggestion = suggest_rephrasing(emotion)

        conn = sqlite3.connect("data.db")
        c = conn.cursor()
        c.execute("INSERT INTO comments (user_id, text, hate_label, hate_conf, emotion_label, emotion_conf, suggestion) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (session["user_id"], text, result, confidence, emotion, emotion_conf, suggestion))
        conn.commit()
        conn.close()

    return render_template("index.html", result=result, confidence=confidence, emotion=emotion, emotion_conf=emotion_conf, suggestion=suggestion)

# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("data.db")
        c = conn.cursor()
        c.execute("SELECT id, password, is_admin FROM users WHERE username=?", (username,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[1], password):
            session["user_id"] = user[0]
            session["is_admin"] = user[2] == 1
            return redirect(url_for("index"))
        flash("Invalid username or password.")
    return render_template("login.html")

# Register
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])
        try:
            conn = sqlite3.connect("data.db")
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username already exists.")
    return render_template("register.html")

# Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# View comment history
@app.route("/history")
def history():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("SELECT text, hate_label, hate_conf, emotion_label, emotion_conf, suggestion FROM comments WHERE user_id=? ORDER BY id DESC", (session["user_id"],))
    records = c.fetchall()
    conn.close()

    return render_template("history.html", records=records)

# Admin dashboard
@app.route("/admin")
def admin():
    if not session.get("is_admin"):
        return redirect(url_for("login"))

    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("SELECT users.username, text, hate_label, hate_conf, emotion_label, emotion_conf FROM comments JOIN users ON comments.user_id = users.id ORDER BY comments.id DESC")
    records = c.fetchall()
    conn.close()

    return render_template("admin.html", records=records)

# Run the app
if __name__ == "__main__":
    print("Flask app running at http://127.0.0.1:5000/")
    app.run(debug=True)
