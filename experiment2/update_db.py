import sqlite3

# Connect to the existing database
conn = sqlite3.connect("data.db")
c = conn.cursor()

# Add a new column for admin if it doesn't already exist
try:
    c.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
    print("✅ 'is_admin' column added successfully.")
except sqlite3.OperationalError:
    print("⚠️ 'is_admin' column already exists. Skipping.")

conn.commit()
conn.close()
