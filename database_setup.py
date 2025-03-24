import sqlite3

conn = sqlite3.connect('coal_mines.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS mines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    latitude REAL,
    longitude REAL,
    co2 REAL,
    ch4 REAL
)
''')

# Sample data
cursor.execute("INSERT INTO mines (name, latitude, longitude, co2, ch4) VALUES ('Mine A', 23.6345, 78.9629, 210, 120)")
cursor.execute("INSERT INTO mines (name, latitude, longitude, co2, ch4) VALUES ('Mine B', 24.6354, 79.9630, 190, 80)")

conn.commit()
conn.close()
