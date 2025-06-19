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

# Remove accidental "static/" prefix before Cloudinary URLs
cursor.execute(
    """
    UPDATE vehicle
    SET photo = substr(photo, 8)
    WHERE photo LIKE 'static/http%'
    """
)

cursor.execute(
    """
    UPDATE expense
    SET receipt_photo = REPLACE(receipt_photo, 'Uploads/', 'uploads/')
    WHERE receipt_photo LIKE 'Uploads/%'
    """
)

cursor.execute(
    """
    UPDATE expense
    SET receipt_photo = substr(receipt_photo, 8)
    WHERE receipt_photo LIKE 'static/http%'
    """
)

conn.commit()
conn.close()
