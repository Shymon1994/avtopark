import sqlite3

conn = sqlite3.connect("instance/fleet.db")
cursor = conn.cursor()

cursor.execute("""
UPDATE vehicle
SET photo = REPLACE(photo, 'Uploads/', 'uploads/')
WHERE photo LIKE 'Uploads/%'
""")

conn.commit()
conn.close()
