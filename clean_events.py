import sqlite3

DB = 'database.db'

def clean_events_table():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    # Remove events with NULL or missing id (shouldn't exist, but just in case)
    cur.execute('DELETE FROM events WHERE id IS NULL')
    # Optionally, print all events to verify
    for row in cur.execute('SELECT id, name, year FROM events'):
        print(row)
    conn.commit()
    conn.close()

if __name__ == '__main__':
    clean_events_table()
    print('Cleaned events table.')
    
