import sqlite3
from pathlib import Path

DB_NAME = "sensors.db"
DB_PATH = Path(__file__).parent.parent / DB_NAME

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("CREATE TABLE IF NOT EXISTS reading (id INTEGER PRIMARY KEY AUTOINCREMENT, sensor TEXT, property TEXT, temp REAL, ts DATETIME DEFAULT CURRENT_TIMESTAMP)")
        conn.execute("CREATE TABLE IF NOT EXISTS current_status (sensor TEXT, property TEXT, temp REAL, ts DATETIME, PRIMARY KEY (sensor, property))")
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS update_current_status AFTER INSERT ON reading
            BEGIN
                INSERT INTO current_status (sensor, property, temp, ts) 
                VALUES (NEW.sensor, NEW.property, NEW.temp, NEW.ts)
                ON CONFLICT(sensor, property) DO UPDATE SET temp = excluded.temp, ts = excluded.ts;
            END
        """)
        conn.commit()

def save_reading(name, prop, val):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT INTO reading (sensor, property, temp) VALUES (?, ?, ?)", (name, prop, val))
        conn.commit()

def get_current_status():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("SELECT sensor, property, temp, ts FROM current_status")
        return [{"sensor": r[0], "prop": r[1], "temp": r[2], "ts": r[3]} for r in cursor.fetchall()]