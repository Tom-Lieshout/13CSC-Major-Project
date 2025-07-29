import sqlite3
conn = sqlite3.connect('database.db')
conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (
    'admin',
    'scrypt:32768:8:1$3dntMsCEiE4bqwyA$349ddbd77c94dc76d4dff2b2a763921c8d2fb4735d27735bf3a6bf85d1acdbd6e193da4e976624feadf298f5fec3aa5dd659f08db63be6737ea6af1b6f91102f'
))
conn.commit()
conn.close()
print("Admin user inserted.")