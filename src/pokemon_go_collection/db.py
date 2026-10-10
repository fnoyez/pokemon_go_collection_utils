import contextlib
import sqlite3


@contextlib.contextmanager
def db_conn(db_file_path):
    """Yield a connection, committing when the block succeeds and closing it in any case."""
    conn = get_connection(db_file_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def get_connection(db_file_path):
    conn = sqlite3.connect(db_file_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn
