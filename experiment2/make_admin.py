import sqlite3

# Change this to the username you want to make admin
admin_username = "mathu"

conn = sqlite3.connect("data.db")
c = conn.cursor()

# Update is_admin to 1 for the given username
c.execute("UPDATE users SET is_admin = 1 WHERE username = ?", (admin_username,))
conn.commit()

if c.rowcount > 0:
    print(f"✅ User '{admin_username}' is now an admin.")
else:
    print(f"⚠️ No such user '{admin_username}' found. Did you register them already?")

conn.close()
