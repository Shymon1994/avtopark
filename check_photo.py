import sqlite3

conn = sqlite3.connect("instance/fleet.db")
cursor = conn.cursor()
cursor.execute("SELECT id, license_plate, photo FROM vehicle")
for row in cursor.fetchall():
    print(row)
conn.close()
