import sqlite3

conn = sqlite3.connect("instance/fleet.db")
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE vehicle ADD COLUMN photo TEXT")
    print("Стовпець 'photo' успішно додано.")
except sqlite3.OperationalError as e:
    print("Помилка:", e)

conn.commit()
conn.close()
