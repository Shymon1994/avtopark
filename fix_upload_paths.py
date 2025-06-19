import sqlite3

DB_PATH = "instance/fleet.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute(
    """
    UPDATE vehicle
    SET photo = REPLACE(photo, 'Uploads/', 'uploads/')
    WHERE photo LIKE 'Uploads/%'
    """
)

cursor.execute(
    """
    UPDATE expense
    SET receipt_photo = REPLACE(receipt_photo, 'Uploads/', 'uploads/')
    WHERE receipt_photo LIKE 'Uploads/%'
    """
)

conn.commit()
conn.close()
