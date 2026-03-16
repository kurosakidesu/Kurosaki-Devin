import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "..", "transfer_order.db"))


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create tables and insert seed data."""
    conn = get_connection()
    cursor = conn.cursor()

    # -- m_shipping_sts (出荷ステータスマスタ)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS m_shipping_sts (
            status_category TEXT NOT NULL,
            shipping_status INTEGER NOT NULL,
            name TEXT,
            abbreviation TEXT,
            list_order INTEGER,
            PRIMARY KEY (status_category, shipping_status)
        )
    """)

    # -- m_code_name_pair (名称・区分マスタ)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS m_code_name_pair (
            name_type TEXT NOT NULL,
            name_code TEXT NOT NULL,
            name TEXT,
            PRIMARY KEY (name_type, name_code)
        )
    """)

    # -- m_bat (バッチマスタ)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS m_bat (
            batch_no TEXT PRIMARY KEY,
            batch_name TEXT,
            marine_transfer_category INTEGER DEFAULT 0,
            flowmeter_name1 TEXT,
            batch_flag_tag TEXT,
            batch_lock_no1 TEXT,
            batch_lock_no2 TEXT,
            batch_lock_no3 TEXT,
            batch_lock_no4 TEXT,
            batch_lock_no5 TEXT,
            batch_lock_no6 TEXT,
            batch_lock_no7 TEXT,
            batch_lock_no8 TEXT,
            batch_lock_no9 TEXT,
            batch_lock_no10 TEXT
        )
    """)

    # -- m_bat_item (バッチ管理品名マスタ)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS m_bat_item (
            batch_no TEXT NOT NULL,
            item_code TEXT NOT NULL,
            PRIMARY KEY (batch_no, item_code)
        )
    """)

    # -- transfer_order (移送オーダ)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transfer_order (
            internal_no TEXT NOT NULL,
            slip_branch_no TEXT NOT NULL,
            transfer_date TEXT,
            slip_no TEXT,
            from_tank_no TEXT,
            to_tank_no TEXT,
            item_code TEXT,
            item_name TEXT,
            shipping_status INTEGER DEFAULT 0,
            batch_no TEXT,
            PRIMARY KEY (internal_no, slip_branch_no)
        )
    """)

    # -- transfer_record (移送実績)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transfer_record (
            internal_no TEXT NOT NULL,
            slip_branch_no TEXT NOT NULL,
            reserved_quantity_converted REAL,
            modified_reserve_unit_code TEXT,
            oil1_tank1_net REAL,
            oil1_tank2_net REAL,
            oil1_tank3_net REAL,
            oil1_tank1_gross REAL,
            oil1_tank2_gross REAL,
            oil1_tank3_gross REAL,
            transfer_start_datetime TEXT,
            transfer_end_datetime TEXT,
            oil1_flowmeter TEXT,
            PRIMARY KEY (internal_no, slip_branch_no)
        )
    """)

    # -- locking_bat (ロック中バッチ)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS locking_bat (
            batch_no TEXT NOT NULL,
            lock_source_internal_no TEXT,
            lock_source_slip_no TEXT,
            lock_source_slip_branch_no TEXT,
            lock_source_batch_no TEXT,
            PRIMARY KEY (batch_no, lock_source_internal_no, lock_source_slip_branch_no)
        )
    """)

    conn.commit()
    conn.close()


def seed_db():
    """Insert sample data for testing."""
    conn = get_connection()
    cursor = conn.cursor()

    # Check if data already exists
    cursor.execute("SELECT COUNT(*) FROM transfer_order")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    # -- 出荷ステータスマスタ (status_category=4: 移送)
    statuses = [
        ("4", 0,  "予約",         "予約",   1),
        ("4", 1,  "バッチ割当",   "割当",   2),
        ("4", 5,  "DCS送信",      "DCS送",  3),
        ("4", 15, "DCS再送",      "DCS再",  4),
        ("4", 20, "移送中",       "移送中", 5),
        ("4", 26, "一時停止",     "一停",   6),
        ("4", 40, "実績保留",     "実保",   7),
        ("4", 41, "実績送信完了", "完了",   8),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO m_shipping_sts VALUES (?,?,?,?,?)", statuses
    )

    # -- 名称・区分マスタ (name_type=01: 単位)
    units = [
        ("01", "01", "kL"),
        ("01", "02", "L"),
        ("01", "03", "m3"),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO m_code_name_pair VALUES (?,?,?)", units
    )

    # -- バッチマスタ
    batches = [
        ("B001", "移送バッチA", 2, "FM-001", "TAG-A", None, None, None, None, None, None, None, None, None, None),
        ("B002", "移送バッチB", 2, "FM-002", "TAG-A", None, None, None, None, None, None, None, None, None, None),
        ("B003", "移送バッチC", 3, "FM-003", "TAG-B", "B004", None, None, None, None, None, None, None, None, None),
        ("B004", "移送バッチD", 3, "FM-004", "TAG-B", "B003", None, None, None, None, None, None, None, None, None),
        ("B005", "移送バッチE", 1, "FM-005", "TAG-C", None, None, None, None, None, None, None, None, None, None),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO m_bat VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", batches
    )

    # -- バッチ管理品名マスタ
    bat_items = [
        ("B001", "P001"),
        ("B001", "P002"),
        ("B002", "P001"),
        ("B002", "P003"),
        ("B003", "P002"),
        ("B003", "P004"),
        ("B004", "P001"),
        ("B004", "P005"),
        ("B005", "P001"),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO m_bat_item VALUES (?,?)", bat_items
    )

    # -- 移送オーダ (20 records with various statuses and dates)
    import datetime
    today = datetime.date.today().isoformat()
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()

    orders = [
        # (internal_no, slip_branch_no, transfer_date, slip_no, from_tank, to_tank, item_code, item_name, status, batch_no)
        ("IM0001", "01", today, "T10001", "TK-101", "TK-201", "P001", "レギュラーガソリン", 0, None),
        ("IM0002", "01", today, "T10002", "TK-102", "TK-202", "P002", "ハイオクガソリン", 0, None),
        ("IM0003", "01", today, "T10003", "TK-103", "TK-203", "P001", "レギュラーガソリン", 1, "B001"),
        ("IM0004", "01", today, "T10004", "TK-104", "TK-204", "P003", "軽油", 5, "B002"),
        ("IM0005", "01", today, "T10005", "TK-101", "TK-205", "P004", "灯油", 20, "B003"),
        ("IM0005", "02", today, "T10005", "TK-101", "TK-206", "P004", "灯油", 20, "B003"),
        ("IM0006", "01", today, "T10006", "TK-105", "TK-207", "P002", "ハイオクガソリン", 26, "B004"),
        ("IM0007", "01", today, "T10007", "TK-106", "TK-208", "P005", "A重油", 40, "B001"),
        ("IM0008", "01", today, "T10008", "TK-107", "TK-209", "P001", "レギュラーガソリン", 41, "B002"),
        ("IM0009", "01", today, "T10009", "TK-108", "TK-210", "P003", "軽油", 15, "B003"),
        ("IM0010", "01", today, "T10010", "TK-109", "TK-211", "P001", "レギュラーガソリン", 0, None),
        ("IM0011", "01", yesterday, "T10011", "TK-110", "TK-212", "P002", "ハイオクガソリン", 20, "B001"),
        ("IM0012", "01", yesterday, "T10012", "TK-111", "TK-213", "P004", "灯油", 41, "B004"),
        ("IM0013", "01", yesterday, "T10013", "TK-112", "TK-214", "P005", "A重油", 5, "B002"),
        ("IM0014", "01", tomorrow, "T10014", "TK-113", "TK-215", "P001", "レギュラーガソリン", 0, None),
        ("IM0015", "01", tomorrow, "T10015", "TK-114", "TK-216", "P003", "軽油", 0, None),
        ("IM0016", "01", today, "T10016", "TK-115", "TK-217", "P001", "レギュラーガソリンプレミアムスーパーロング品名テスト", 0, None),
        ("IM0017", "01", today, "T10017", "TK-116", "TK-218", "", "", 0, None),
        ("IM0018", "01", today, "T10018", "TK-117", "TK-219", "P002", "ハイオクガソリン", 1, "B001"),
        ("IM0019", "01", today, "T10019", "TK-118", "TK-220", "P001", "レギュラーガソリン", 41, "B002"),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO transfer_order VALUES (?,?,?,?,?,?,?,?,?,?)", orders
    )

    # -- 移送実績
    records = [
        # (internal_no, slip_branch_no, reserved_qty, unit_code, net1, net2, net3, gross1, gross2, gross3, start, end, flowmeter)
        ("IM0001", "01", 100.500, "01", None, None, None, None, None, None, None, None, None),
        ("IM0002", "01", 200.000, "01", None, None, None, None, None, None, None, None, None),
        ("IM0003", "01", 150.250, "01", 50.100, 30.200, 20.050, 51.000, 31.000, 21.000, None, None, "FM-001"),
        ("IM0004", "01", 300.000, "01", 100.500, 80.300, 50.200, 102.000, 82.000, 52.000, f"{today} 08:30", None, "FM-002"),
        ("IM0005", "01", 500.750, "01", 200.100, 150.200, 100.300, 205.000, 155.000, 105.000, f"{today} 09:00", None, "FM-003"),
        ("IM0005", "02", 250.000, "01", 100.000, 80.000, 50.000, 102.000, 82.000, 52.000, f"{today} 09:00", None, "FM-003"),
        ("IM0006", "01", 180.500, "01", 60.100, 50.200, 40.100, 62.000, 52.000, 42.000, f"{today} 10:00", None, "FM-004"),
        ("IM0007", "01", 420.000, "01", 150.300, 120.200, 80.100, 155.000, 125.000, 85.000, f"{today} 07:00", None, "FM-001"),
        ("IM0008", "01", 320.100, "01", 120.000, 100.000, 80.000, 125.000, 105.000, 85.000, f"{today} 06:00", f"{today} 08:00", "FM-002"),
        ("IM0009", "01", 275.500, "01", 90.100, 80.200, 60.300, 92.000, 82.000, 62.000, f"{today} 11:00", None, "FM-003"),
        ("IM0010", "01", 190.000, "01", None, None, None, None, None, None, None, None, None),
        ("IM0011", "01", 400.250, "01", 180.100, 120.200, 80.050, 185.000, 125.000, 85.000, f"{yesterday} 14:00", None, "FM-001"),
        ("IM0012", "01", 350.000, "01", 130.000, 110.000, 90.000, 135.000, 115.000, 95.000, f"{yesterday} 10:00", f"{yesterday} 15:00", "FM-004"),
        ("IM0013", "01", 280.750, "01", 100.200, 80.300, 60.100, 102.000, 82.000, 62.000, f"{yesterday} 08:00", None, "FM-002"),
        ("IM0014", "01", 160.000, "01", None, None, None, None, None, None, None, None, None),
        ("IM0015", "01", 220.500, "01", None, None, None, None, None, None, None, None, None),
        ("IM0016", "01", 0.000, "01", None, None, None, None, None, None, None, None, None),
        ("IM0017", "01", None, None, None, None, None, None, None, None, None, None, None),
        ("IM0018", "01", 310.000, "01", 100.000, 90.000, 70.000, 105.000, 95.000, 75.000, None, None, "FM-001"),
        ("IM0019", "01", 445.250, "01", 160.000, 140.000, 100.000, 165.000, 145.000, 105.000, f"{today} 05:00", f"{today} 09:00", "FM-002"),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO transfer_record VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", records
    )

    # -- ロック中バッチ (some locked batches for testing)
    locked = [
        ("B003", "IM0005", "T10005", "01", "B003"),
        ("B004", "IM0005", "T10005", "01", "B003"),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO locking_bat VALUES (?,?,?,?,?)", locked
    )

    conn.commit()
    conn.close()
