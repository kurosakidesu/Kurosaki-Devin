"""Database setup and initialization for land order list screen."""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "land_order.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create tables and seed data on startup."""
    conn = get_connection()
    cur = conn.cursor()

    # ---- m_shipping_sts (出荷ステータスマスタ) ----
    cur.execute("""
        CREATE TABLE IF NOT EXISTS m_shipping_sts (
            status_category  INTEGER NOT NULL,  -- ステータス区分 (1=陸上)
            shipping_type    TEXT    NOT NULL,  -- 出荷形態
            shipping_status  INTEGER NOT NULL,  -- 出荷ステータス
            status_name      TEXT,              -- ステータス名
            abbreviation     TEXT,              -- 略称
            list_order       INTEGER,           -- 一覧順
            PRIMARY KEY (status_category, shipping_type, shipping_status)
        )
    """)

    # ---- m_code_name_pair (名称・区分マスタ) ----
    cur.execute("""
        CREATE TABLE IF NOT EXISTS m_code_name_pair (
            name_type   TEXT NOT NULL,  -- 名称種別
            name_code   TEXT NOT NULL,  -- 名称コード
            name_value  TEXT,           -- 名称
            PRIMARY KEY (name_type, name_code)
        )
    """)

    # ---- lane_situ (レーン利用状況) ----
    cur.execute("""
        CREATE TABLE IF NOT EXISTS lane_situ (
            lane_no      INTEGER PRIMARY KEY,
            in_operation INTEGER DEFAULT 1  -- 1=操業中
        )
    """)

    # ---- land_order (陸上オーダ) ----
    cur.execute("""
        CREATE TABLE IF NOT EXISTS land_order (
            internal_no       TEXT    NOT NULL,  -- 内部管理No
            slip_branch_no    TEXT    NOT NULL,  -- 伝票枝番
            shipping_date     TEXT,              -- 出荷日 (YYYY-MM-DD)
            slip_no           TEXT,              -- 伝票No
            car_no            TEXT,              -- 車番
            destination_name  TEXT,              -- 届け先名
            min_product_code  TEXT,              -- 最小品名コード
            min_product_name  TEXT,              -- 最小品名
            mgmt_product_code TEXT,              -- 管理品名コード
            mgmt_product_name TEXT,              -- 管理品名
            reservation_qty   REAL,              -- 予約数量
            reservation_unit  TEXT,              -- 予約単位コード (10=kg,20=t,other=kL)
            shipping_type     TEXT,              -- 出荷形態
            shipping_status   INTEGER DEFAULT 0, -- 出荷ステータス
            ukeharai_kbn      TEXT,              -- 受払区分
            ukewatashi_cond   TEXT,              -- 受渡条件
            trip              INTEGER,           -- TRIP
            remarks           TEXT,              -- 備考
            PRIMARY KEY (internal_no, slip_branch_no)
        )
    """)

    # ---- land_record (陸上実績) ----
    cur.execute("""
        CREATE TABLE IF NOT EXISTS land_record (
            internal_no           TEXT NOT NULL,  -- 内部管理No
            slip_branch_no        TEXT NOT NULL,  -- 伝票枝番
            admission_datetime    TEXT,           -- 入門日時
            loading_end_datetime  TEXT,           -- 積込終了日時
            lane_no               INTEGER,        -- レーンNo
            tank1_1_no            TEXT,           -- 油種1_タンク1_タンクNo
            tank1_2_no            TEXT,           -- 油種1_タンク2_タンクNo
            tank1_3_no            TEXT,           -- 油種1_タンク3_タンクNo
            tank2_1_no            TEXT,           -- 油種2_タンク1_タンクNo
            tank2_2_no            TEXT,           -- 油種2_タンク2_タンクNo
            tank2_3_no            TEXT,           -- 油種2_タンク3_タンクNo
            result_qty            REAL,           -- 実績数量
            corrected_result_unit TEXT,           -- 修正実績単位コード (00=kL, 01=kg, 10=kg)
            corrected_reservation_unit TEXT,      -- 修正予約単位コード
            reservation_qty_converted  REAL,      -- 予約数量(換算値)
            weighing_result       TEXT,           -- 計量実績値
            result_date           TEXT,           -- 実績日
            PRIMARY KEY (internal_no, slip_branch_no)
        )
    """)

    conn.commit()
    conn.close()


def seed_data():
    """Insert sample data (20+ records)."""
    conn = get_connection()
    cur = conn.cursor()

    # Check if already seeded
    cur.execute("SELECT COUNT(*) FROM land_order")
    if cur.fetchone()[0] > 0:
        conn.close()
        return

    # ---- m_shipping_sts seed ----
    shipping_sts_data = [
        # (status_category, shipping_type, shipping_status, status_name, abbreviation, list_order)
        (1, "01", 0,  "予約",             "予約",     1),
        (1, "01", 5,  "入門受付",         "入門",     2),
        (1, "01", 10, "前計量済",         "前計量",   3),
        (1, "01", 15, "前計量完了",       "前計量完", 4),
        (1, "01", 20, "レーン入線",       "入線",     5),
        (1, "01", 25, "積込完了",         "積込完",   6),
        (1, "01", 30, "T/S（後計量）受付","後計量",   7),
        (1, "01", 35, "後計量完了",       "後計量完", 8),
        (1, "01", 40, "実績保留",         "実績保留", 9),
        (1, "01", 41, "実績送信完了",     "実績完",   10),
        (1, "02", 0,  "予約",             "予約",     1),
        (1, "02", 5,  "入門受付",         "入門",     2),
        (1, "02", 10, "前計量済",         "前計量",   3),
        (1, "02", 15, "前計量完了",       "前計量完", 4),
        (1, "02", 20, "レーン入線",       "入線",     5),
        (1, "02", 25, "積込完了",         "積込完",   6),
        (1, "02", 30, "T/S（後計量）受付","後計量",   7),
        (1, "02", 35, "後計量完了",       "後計量完", 8),
        (1, "02", 40, "実績保留",         "実績保留", 9),
        (1, "02", 41, "実績送信完了",     "実績完",   10),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO m_shipping_sts VALUES (?,?,?,?,?,?)",
        shipping_sts_data,
    )

    # ---- m_code_name_pair seed ----
    code_name_data = [
        # 名称種別 11: 受払区分
        ("11", "01", "受"),
        ("11", "02", "払"),
        ("11", "03", "振替"),
        # 名称種別 13: 受渡条件
        ("13", "01", "持込"),
        ("13", "02", "引取"),
        ("13", "03", "直送"),
        # 名称種別 14: 出荷形態
        ("14", "01", "ローリー"),
        ("14", "02", "ドラム"),
        # 名称種別 01: 単位
        ("01", "00", "kL"),
        ("01", "01", "kg"),
        ("01", "10", "kg"),
        ("01", "20", "t"),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO m_code_name_pair VALUES (?,?,?)",
        code_name_data,
    )

    # ---- lane_situ seed ----
    for lane in range(1, 6):
        cur.execute("INSERT OR IGNORE INTO lane_situ VALUES (?, 1)", (lane,))

    # ---- land_order seed (20+ records) ----
    import datetime
    today = datetime.date.today().isoformat()
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()

    orders = [
        # (internal_no, slip_branch_no, shipping_date, slip_no, car_no, destination_name,
        #  min_product_code, min_product_name, mgmt_product_code, mgmt_product_name,
        #  reservation_qty, reservation_unit, shipping_type, shipping_status,
        #  ukeharai_kbn, ukewatashi_cond, trip, remarks)
        ("ORD001", "01", today, "D00101", "品川100あ1234", "東京石油ターミナル", "P001", "レギュラーガソリン", "M001", "ガソリン", 20000, "10", "01", 0, "02", "01", 1, "通常配送"),
        ("ORD002", "01", today, "D00201", "横浜200か5678", "横浜油槽所", "P002", "ハイオクガソリン", "M001", "ガソリン", 15000, "10", "01", 5, "02", "02", 1, ""),
        ("ORD002", "02", today, "D00201", "横浜200か5678", "横浜油槽所", "P003", "軽油", "M002", "軽油", 10000, "10", "01", 5, "02", "02", 1, "枝番2"),
        ("ORD003", "01", today, "D00301", "川崎300さ9012", "川崎物流センター", "P003", "軽油", "M002", "軽油", 25.5, "20", "01", 10, "01", "01", 1, ""),
        ("ORD004", "01", today, "D00401", "千葉400た3456", "千葉港油槽所", "P004", "灯油", "M003", "灯油", 18.750, None, "02", 20, "02", "03", 2, "特急対応"),
        ("ORD005", "01", today, "D00501", "埼玉500な7890", "埼玉配送センター", "P001", "レギュラーガソリン", "M001", "ガソリン", 30000, "10", "01", 25, "02", "01", 1, ""),
        ("ORD006", "01", today, "D00601", "神奈川600は1234", "相模原デポ", "P005", "A重油", "M004", "重油", 15.200, None, "01", 30, "01", "02", 1, ""),
        ("ORD007", "01", today, "D00701", "東京700ま5678", "大田区油槽所", "P002", "ハイオクガソリン", "M001", "ガソリン", 20000, "10", "01", 35, "02", "01", 1, "備考テスト用の長いテキストが入ります。この備考欄は長文テストのためのサンプルデータです。"),
        ("ORD008", "01", today, "D00801", "茨城800や9012", "鹿島臨海工業地帯", "P006", "C重油", "M004", "重油", 50.000, None, "02", 40, "01", "03", 1, ""),
        ("ORD009", "01", today, "D00901", "栃木900ら3456", "宇都宮SS", "P001", "レギュラーガソリン", "M001", "ガソリン", 16000, "10", "01", 41, "02", "01", 3, ""),
        ("ORD010", "01", today, "D01001", "群馬100い7890", "前橋油槽所", "P003", "軽油", "M002", "軽油", 22000, "10", "01", 0, "02", "02", 1, ""),
        ("ORD011", "01", today, "D01101", "千葉200う1234", "市原コンビナート", "P004", "灯油", "M003", "灯油", 12.500, None, "01", 5, "01", "01", 1, ""),
        ("ORD012", "01", today, "D01201", "東京300え5678", "品川埠頭", "P005", "A重油", "M004", "重油", 35.000, None, "02", 15, "02", "03", 2, ""),
        ("ORD013", "01", today, "D01301", "神奈川400お9012", "横須賀基地", "P002", "ハイオクガソリン", "M001", "ガソリン", 18000, "10", "01", 20, "02", "01", 1, "防衛省向け"),
        ("ORD014", "01", today, "D01401", "埼玉500か3456", "川口石油基地", "P001", "レギュラーガソリン", "M001", "ガソリン", 28000, "10", "01", 25, "02", "02", 1, ""),
        ("ORD015", "01", yesterday, "D01501", "品川600き7890", "東京湾岸ターミナル", "P003", "軽油", "M002", "軽油", 20000, "10", "01", 10, "01", "01", 1, "前日分未完了"),
        ("ORD016", "01", yesterday, "D01601", "横浜700く1234", "根岸製油所", "P006", "C重油", "M004", "重油", 45.000, None, "02", 41, "02", "03", 1, ""),
        ("ORD017", "01", tomorrow, "D01701", "川崎800け5678", "扇島石油基地", "P004", "灯油", "M003", "灯油", 14000, "10", "01", 0, "02", "01", 1, "翌日分予約"),
        ("ORD018", "01", today, "D01801", "", "名称未設定届け先", "", "", "", "", None, "10", "01", 0, "", "", 1, ""),
        ("ORD019", "01", today, "D01901", "静岡100こ9999", "清水港LNG基地ターミナル株式会社東海支店第二倉庫", "P007", "ナフサ特殊グレードABC-123長い品名テスト", "M005", "ナフサ特殊品", 99999, "10", "01", 5, "03", "01", 1, ""),
        ("ORD020", "01", today, "D02001", "愛知200さ1111", "名古屋港油槽所", "P001", "レギュラーガソリン", "M001", "ガソリン", 24000, "10", "01", 40, "02", "02", 2, "実績保留テスト"),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO land_order VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        orders,
    )

    # ---- land_record seed ----
    records = [
        # (internal_no, slip_branch_no, admission_datetime, loading_end_datetime, lane_no,
        #  tank1_1_no, tank1_2_no, tank1_3_no, tank2_1_no, tank2_2_no, tank2_3_no,
        #  result_qty, corrected_result_unit, corrected_reservation_unit, reservation_qty_converted,
        #  weighing_result, result_date)
        ("ORD002", "01", f"{today} 08:30", None, None, None, None, None, None, None, None, None, None, None, None, None, None),
        ("ORD002", "02", f"{today} 08:30", None, None, None, None, None, None, None, None, None, None, None, None, None, None),
        ("ORD003", "01", f"{today} 07:15", None, None, "T-101", None, None, None, None, None, None, None, "20", 25.500, None, None),
        ("ORD004", "01", f"{today} 06:45", None, 2, "T-201", "T-202", None, None, None, None, None, None, None, 18.750, None, None),
        ("ORD005", "01", f"{today} 09:00", None, 3, "T-301", None, None, None, None, None, None, None, None, None, "28500", None),
        ("ORD006", "01", f"{today} 07:30", None, 1, "T-102", None, None, None, None, None, 14.800, "00", None, 15.200, "14800", None),
        ("ORD007", "01", f"{today} 06:00", f"{today} 10:30", 4, "T-401", None, None, None, None, None, 19500, "01", "10", None, "19500", None),
        ("ORD008", "01", f"{today} 08:00", f"{today} 11:45", 2, "T-501", None, None, None, None, None, 48.500, "00", None, 50.000, "48500", today),
        ("ORD009", "01", f"{today} 05:30", f"{today} 09:15", 1, "T-301", None, None, None, None, None, 15800, "01", "10", None, "15800", today),
        ("ORD011", "01", f"{today} 10:15", None, None, None, None, None, None, None, None, None, None, None, None, None, None),
        ("ORD012", "01", f"{today} 09:45", None, 3, "T-601", None, None, None, None, None, None, None, None, None, None, None),
        ("ORD013", "01", f"{today} 08:15", None, 5, "T-701", None, None, None, None, None, None, None, None, None, None, None),
        ("ORD014", "01", f"{today} 07:00", None, 4, "T-301", None, None, None, None, None, None, None, None, None, "27800", None),
        ("ORD015", "01", f"{yesterday} 14:30", None, 2, "T-101", None, None, None, None, None, None, None, None, None, None, None),
        ("ORD016", "01", f"{yesterday} 06:00", f"{yesterday} 12:00", 1, "T-801", None, None, None, None, None, 44.200, "00", None, 45.000, "44200", yesterday),
        ("ORD019", "01", f"{today} 11:00", None, None, None, None, None, None, None, None, None, None, None, None, None, None),
        ("ORD020", "01", f"{today} 06:30", f"{today} 10:00", 3, "T-901", None, None, None, None, None, 23800, "01", "10", None, "23800", today),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO land_record VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        records,
    )

    conn.commit()
    conn.close()
