import sqlite3
from pathlib import Path
from typing import List
from contextlib import contextmanager
import threading

from src.config import config
from src.logger import logger
from src.models import SensorReading

DB_PATH = Path(__file__).parent.parent / config.DB_NAME

# Thread-local storage for database connections (connection pool)
# This prevents creating new connections on every operation
_thread_local = threading.local()


def _get_connection() -> sqlite3.Connection:
    """
    Get a thread-local database connection (connection pooling).

    This reuses connections within the same thread, reducing overhead
    which is critical for Raspberry Pi's limited resources.
    """
    if not hasattr(_thread_local, 'connection') or _thread_local.connection is None:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        # Apply pragmas to the connection
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA wal_autocheckpoint=1000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        _thread_local.connection = conn
        logger.debug(f"Created new DB connection for thread {threading.get_ident()}")
    return _thread_local.connection


@contextmanager
def get_db_connection():
    """
    Context manager for getting a database connection.

    Usage:
        with get_db_connection() as conn:
            conn.execute(...)
    """
    conn = _get_connection()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    else:
        conn.commit()


def close_all_connections():
    """Close all thread-local connections. Call during shutdown."""
    if hasattr(_thread_local, 'connection') and _thread_local.connection:
        _thread_local.connection.close()
        _thread_local.connection = None
        logger.debug("Closed DB connection")


def init_db() -> None:
    """Initialize database with required tables and triggers."""
    try:
        with get_db_connection() as conn:
            # Create readings table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reading (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sensor TEXT NOT NULL,
                    property TEXT NOT NULL,
                    temp REAL NOT NULL,
                    ts DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create current status table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS current_status (
                    sensor TEXT NOT NULL,
                    property TEXT NOT NULL,
                    temp REAL NOT NULL,
                    ts DATETIME NOT NULL,
                    PRIMARY KEY (sensor, property)
                )
            """)

            # Create trigger to auto-update current status
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS update_current_status
                AFTER INSERT ON reading
                BEGIN
                    INSERT INTO current_status (sensor, property, temp, ts)
                    VALUES (NEW.sensor, NEW.property, NEW.temp, NEW.ts)
                    ON CONFLICT(sensor, property)
                    DO UPDATE SET temp = excluded.temp, ts = excluded.ts;
                END
            """)

            # Create index on timestamp for efficient pruning queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_reading_ts ON reading(ts)
            """)

            logger.debug(f"Database initialized at {DB_PATH}")

    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")
        raise


def save_reading(name: str, prop: str, val: float) -> None:
    """Save a sensor reading to the database using connection pool."""
    try:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO reading (sensor, property, temp) VALUES (?, ?, ?)",
                (name, prop, val)
            )
    except sqlite3.Error as e:
        logger.error(f"Failed to save reading for {name}/{prop}: {e}")
        raise


def get_current_status() -> List[SensorReading]:
    """Retrieve the current status of all sensors using connection pool."""
    try:
        conn = _get_connection()
        cursor = conn.execute(
            "SELECT sensor, property, temp, ts FROM current_status ORDER BY sensor, property"
        )
        return [
            SensorReading(
                sensor=row[0],
                prop=row[1],
                temp=row[2],
                ts=row[3]
            )
            for row in cursor.fetchall()
        ]
    except sqlite3.Error as e:
        logger.error(f"Failed to get current status: {e}")
        return []


def get_database_stats() -> dict:
    """Get database statistics for monitoring."""
    try:
        conn = _get_connection()

        # Get row counts
        reading_count = conn.execute("SELECT COUNT(*) FROM reading").fetchone()[0]
        current_count = conn.execute("SELECT COUNT(*) FROM current_status").fetchone()[0]

        # Get database file size
        db_size_mb = DB_PATH.stat().st_size / (1024 * 1024) if DB_PATH.exists() else 0

        return {
            "total_readings": reading_count,
            "active_sensors": current_count,
            "db_size_mb": round(db_size_mb, 2)
        }
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        return {}


def cleanup_old_readings(days_to_keep: int = 30) -> int:
    """
    Delete readings older than specified days and reclaim disk space.

    This is critical for Raspberry Pi to prevent SD card from filling up.
    The reading table grows unbounded without cleanup, eventually causing
    system failures when storage is exhausted.

    Args:
        days_to_keep: Number of days of readings to retain (default: 30)

    Returns:
        Number of rows deleted

    Raises:
        sqlite3.Error: If database operation fails
    """
    try:
        with get_db_connection() as conn:
            # Delete old readings
            cursor = conn.execute(
                "DELETE FROM reading WHERE ts < datetime('now', ? || ' days')",
                (f"-{days_to_keep}",)
            )
            deleted_count = cursor.rowcount

            if deleted_count > 0:
                # Reclaim disk space by running VACUUM
                # This rewrites the database file without the deleted data
                conn.execute("VACUUM")
                logger.info(f"🧹 Cleaned up {deleted_count} old readings (older than {days_to_keep} days)")
            else:
                logger.debug(f"🧹 No old readings to clean up (keeping last {days_to_keep} days)")

            return deleted_count

    except sqlite3.Error as e:
        logger.error(f"Failed to cleanup old readings: {e}", exc_info=True)
        raise

