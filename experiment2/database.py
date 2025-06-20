import sqlite3

def init_db():
    conn = sqlite3.connect('comments.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS flagged_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            hate_label TEXT,
            emotion TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_comment(text, hate_label, emotion):
    conn = sqlite3.connect('comments.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO flagged_comments (text, hate_label, emotion)
        VALUES (?, ?, ?)
    ''', (text, hate_label, emotion))
    conn.commit()
    conn.close()
