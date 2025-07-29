import sqlite3

hashed_pw = 'scrypt:32768:8:1$DiCrKz0UJ0NdBnzp$05973658159d1df85708e771c03cc7b17cae9a6934280f68b815b79323cdd4f108090d1ead61073ba113f67770f33841f3cd37bea4e3cb470727dc2aa17e0b93'
users = [
    ('Admin', hashed_pw),
    ('Admin1', hashed_pw),
    ('Admin2', hashed_pw)
]

conn = sqlite3.connect('database.db')
for username, password in users:
    conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
conn.commit()
conn.close()
print("Users inserted.")
