

import sqlite3
from werkzeug.security import generate_password_hash


def insert_default_users():
    db = sqlite3.connect('database.db')
    users = [
        ('admin1', 'password'),
        ('admin2', 'password'),
        ('admin3', 'password')
    ]
    for username, password in users:
        hashed = generate_password_hash(password)
        db.execute("INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)", (username, hashed))
    db.commit()
    db.close()

if __name__ == '__main__':
    insert_default_users()
