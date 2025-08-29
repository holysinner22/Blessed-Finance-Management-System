# db.py
import sqlite3

def get_db_connection():
    conn = sqlite3.connect('school_finance.db')
    conn.row_factory = sqlite3.Row
    return conn

# ------------------------------
# Utility: Reorder expense IDs
# ------------------------------
def reorder_expense_ids():
    """
    Reorders IDs in the expenses table to always be sequential (1, 2, 3, ...).
    WARNING: This is safe here because no other table references expenses.id.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM expenses ORDER BY id")
    all_ids = cursor.fetchall()

    new_id = 1
    for (old_id,) in all_ids:
        if old_id != new_id:  # only update if needed
            cursor.execute("UPDATE expenses SET id = ? WHERE id = ?", (new_id, old_id))
        new_id += 1
    conn.commit()

    # Reset autoincrement sequence
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='expenses'")
    conn.commit()

    conn.close()
    print("✅ Expense IDs reordered")

# ------------------------------
# Migration Helpers
# ------------------------------
def column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return column in [col[1] for col in cursor.fetchall()]

def migrate_fees_table(conn):
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE fees RENAME TO fees_old")

    cursor.execute('''
        CREATE TABLE fees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            category_id INTEGER,
            term TEXT,
            required_amount REAL,
            paid_amount REAL,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(student_id, category_id, term),
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (category_id) REFERENCES fee_categories(id)
        )
    ''')

    cursor.execute('''
        INSERT INTO fees (student_id, category_id, term, required_amount, paid_amount, timestamp)
        SELECT student_id, category_id, term, required_amount, paid_amount, timestamp
        FROM fees_old
    ''')

    cursor.execute("DROP TABLE fees_old")
    print("✅ Migrated fees table to include id column")

# ------------------------------
# Initialization
# ------------------------------
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    if not column_exists(cursor, "users", "role"):
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'staff'")

    # Students table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            parent_phone TEXT,
            class TEXT
        )
    ''')
    if not column_exists(cursor, "students", "parent_phone"):
        cursor.execute("ALTER TABLE students ADD COLUMN parent_phone TEXT")
    if not column_exists(cursor, "students", "class"):
        cursor.execute("ALTER TABLE students ADD COLUMN class TEXT")

    # Fee categories
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fee_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    ''')

    # Notifications table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            phone TEXT,
            message TEXT,
            sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    ''')

    # Reminders log table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders_log (
            student_id INTEGER,
            last_sent TEXT,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    ''')

    # Fees table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            category_id INTEGER,
            term TEXT,
            required_amount REAL,
            paid_amount REAL,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(student_id, category_id, term),
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (category_id) REFERENCES fee_categories(id)
        )
    ''')
    if not column_exists(cursor, "fees", "id"):
        migrate_fees_table(conn)

    # Expenses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT NOT NULL,
            quantity INTEGER,
            cost REAL,
            date TEXT
        )
    ''')
    if not column_exists(cursor, "expenses", "quantity"):
        cursor.execute("ALTER TABLE expenses ADD COLUMN quantity INTEGER DEFAULT 1")

    # Insert default users
    cursor.execute('''
        INSERT OR IGNORE INTO users (username, password, role)
        VALUES 
            ('admin', 'adminpass', 'admin'),
            ('staff', 'staffpass', 'staff')
    ''')

    conn.commit()
    conn.close()

# ------------------------------
# Standalone run
# ------------------------------
if __name__ == "__main__":
    init_db()
    print("✅ Database initialized with auto-migration, including reminders_log")
