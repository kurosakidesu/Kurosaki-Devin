import sqlite3
from typing import Optional

from app.database import get_db


def search_transfer_orders(
    date_from: str,
    date_to: str,
    slip_no: Optional[str] = None,
    from_tank: Optional[str] = None,
    to_tank: Optional[str] = None,
    item_code: Optional[str] = None,
    item_name: Optional[str] = None,
) -> list[dict]:
    """Search transfer orders with join to transfer_record, m_shipping_sts, m_code_name_pair, m_bat."""
    with get_db() as conn:
        query = """
            SELECT
                o.internal_no,
                o.slip_branch_no,
                o.transfer_date,
                o.slip_no,
                o.from_tank_no,
                o.to_tank_no,
                o.item_code,
                o.item_name,
                o.shipping_status,
                o.batch_no,
                s.abbreviation AS status_abbreviation,
                s.list_order AS status_list_order,
                r.reserved_quantity_converted AS plan_quantity_net,
                CASE WHEN r.oil1_tank1_net IS NULL AND r.oil1_tank2_net IS NULL AND r.oil1_tank3_net IS NULL THEN NULL ELSE COALESCE(r.oil1_tank1_net, 0) + COALESCE(r.oil1_tank2_net, 0) + COALESCE(r.oil1_tank3_net, 0) END AS actual_net,
                CASE WHEN r.oil1_tank1_gross IS NULL AND r.oil1_tank2_gross IS NULL AND r.oil1_tank3_gross IS NULL THEN NULL ELSE COALESCE(r.oil1_tank1_gross, 0) + COALESCE(r.oil1_tank2_gross, 0) + COALESCE(r.oil1_tank3_gross, 0) END AS actual_gross,
                r.transfer_start_datetime,
                r.transfer_end_datetime,
                r.modified_reserve_unit_code,
                cnp.name AS unit_name,
                b.batch_name
            FROM transfer_order o
            LEFT JOIN transfer_record r
                ON o.internal_no = r.internal_no AND o.slip_branch_no = r.slip_branch_no
            LEFT JOIN m_shipping_sts s
                ON s.status_category = '4' AND o.shipping_status = s.shipping_status
            LEFT JOIN m_code_name_pair cnp
                ON cnp.name_type = '01' AND r.modified_reserve_unit_code = cnp.name_code
            LEFT JOIN m_bat b
                ON o.batch_no = b.batch_no
            WHERE DATE(o.transfer_date) >= ?
              AND DATE(o.transfer_date) <= ?
        """
        params: list = [date_from, date_to]

        if slip_no:
            query += " AND o.slip_no LIKE ?"
            params.append(f"{slip_no}%")
        if from_tank:
            query += " AND o.from_tank_no = ?"
            params.append(from_tank)
        if to_tank:
            query += " AND o.to_tank_no = ?"
            params.append(to_tank)
        if item_code:
            query += " AND o.item_code LIKE ?"
            params.append(f"{item_code}%")
        if item_name:
            query += " AND o.item_name LIKE ?"
            params.append(f"%{item_name}%")

        query += " ORDER BY s.list_order ASC, o.internal_no ASC, o.slip_branch_no ASC"

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def search_auto_refresh_orders() -> list[dict]:
    """Auto-refresh: today's orders + incomplete orders before today."""
    import datetime
    today = datetime.date.today().isoformat()

    with get_db() as conn:
        # Today's orders
        query_today = """
            SELECT
                o.internal_no,
                o.slip_branch_no,
                o.transfer_date,
                o.slip_no,
                o.from_tank_no,
                o.to_tank_no,
                o.item_code,
                o.item_name,
                o.shipping_status,
                o.batch_no,
                s.abbreviation AS status_abbreviation,
                s.list_order AS status_list_order,
                r.reserved_quantity_converted AS plan_quantity_net,
                CASE WHEN r.oil1_tank1_net IS NULL AND r.oil1_tank2_net IS NULL AND r.oil1_tank3_net IS NULL THEN NULL ELSE COALESCE(r.oil1_tank1_net, 0) + COALESCE(r.oil1_tank2_net, 0) + COALESCE(r.oil1_tank3_net, 0) END AS actual_net,
                CASE WHEN r.oil1_tank1_gross IS NULL AND r.oil1_tank2_gross IS NULL AND r.oil1_tank3_gross IS NULL THEN NULL ELSE COALESCE(r.oil1_tank1_gross, 0) + COALESCE(r.oil1_tank2_gross, 0) + COALESCE(r.oil1_tank3_gross, 0) END AS actual_gross,
                r.transfer_start_datetime,
                r.transfer_end_datetime,
                r.modified_reserve_unit_code,
                cnp.name AS unit_name,
                b.batch_name
            FROM transfer_order o
            LEFT JOIN transfer_record r
                ON o.internal_no = r.internal_no AND o.slip_branch_no = r.slip_branch_no
            LEFT JOIN m_shipping_sts s
                ON s.status_category = '4' AND o.shipping_status = s.shipping_status
            LEFT JOIN m_code_name_pair cnp
                ON cnp.name_type = '01' AND r.modified_reserve_unit_code = cnp.name_code
            LEFT JOIN m_bat b
                ON o.batch_no = b.batch_no
            WHERE DATE(o.transfer_date) = ?
        """

        # Incomplete orders before today (status > 0 and < 41)
        query_incomplete = """
            SELECT
                o.internal_no,
                o.slip_branch_no,
                o.transfer_date,
                o.slip_no,
                o.from_tank_no,
                o.to_tank_no,
                o.item_code,
                o.item_name,
                o.shipping_status,
                o.batch_no,
                s.abbreviation AS status_abbreviation,
                s.list_order AS status_list_order,
                r.reserved_quantity_converted AS plan_quantity_net,
                CASE WHEN r.oil1_tank1_net IS NULL AND r.oil1_tank2_net IS NULL AND r.oil1_tank3_net IS NULL THEN NULL ELSE COALESCE(r.oil1_tank1_net, 0) + COALESCE(r.oil1_tank2_net, 0) + COALESCE(r.oil1_tank3_net, 0) END AS actual_net,
                CASE WHEN r.oil1_tank1_gross IS NULL AND r.oil1_tank2_gross IS NULL AND r.oil1_tank3_gross IS NULL THEN NULL ELSE COALESCE(r.oil1_tank1_gross, 0) + COALESCE(r.oil1_tank2_gross, 0) + COALESCE(r.oil1_tank3_gross, 0) END AS actual_gross,
                r.transfer_start_datetime,
                r.transfer_end_datetime,
                r.modified_reserve_unit_code,
                cnp.name AS unit_name,
                b.batch_name
            FROM transfer_order o
            LEFT JOIN transfer_record r
                ON o.internal_no = r.internal_no AND o.slip_branch_no = r.slip_branch_no
            LEFT JOIN m_shipping_sts s
                ON s.status_category = '4' AND o.shipping_status = s.shipping_status
            LEFT JOIN m_code_name_pair cnp
                ON cnp.name_type = '01' AND r.modified_reserve_unit_code = cnp.name_code
            LEFT JOIN m_bat b
                ON o.batch_no = b.batch_no
            WHERE o.shipping_status > 0
              AND o.shipping_status < 41
              AND DATE(o.transfer_date) < ?
        """

        rows_today = conn.execute(query_today, [today]).fetchall()
        rows_incomplete = conn.execute(query_incomplete, [today]).fetchall()

        combined = [dict(r) for r in rows_today] + [dict(r) for r in rows_incomplete]
        combined.sort(key=lambda x: (x.get("status_list_order") or 999, x["internal_no"], x["slip_branch_no"]))
        return combined


def get_assignable_batches(internal_no: str, slip_branch_no: str) -> list[dict]:
    """Get assignable batches for a given order."""
    with get_db() as conn:
        # Check if batch is already assigned
        order = conn.execute(
            "SELECT batch_no, item_code FROM transfer_order WHERE internal_no = ? AND slip_branch_no = ?",
            [internal_no, slip_branch_no]
        ).fetchone()

        if not order:
            return []

        order_dict = dict(order)

        if order_dict.get("batch_no"):
            # Batch already assigned - return only that batch
            row = conn.execute(
                "SELECT b.batch_no, b.batch_name FROM m_bat b WHERE b.batch_no = ?",
                [order_dict["batch_no"]]
            ).fetchone()
            if row:
                return [dict(row)]
            return []
        else:
            # Batch not assigned - find assignable batches
            item_code = order_dict.get("item_code", "")
            if not item_code:
                return []
            rows = conn.execute(
                """
                SELECT DISTINCT b.batch_no, b.batch_name
                FROM m_bat_item bi
                LEFT JOIN m_bat b ON b.batch_no = bi.batch_no
                WHERE bi.item_code = ?
                  AND b.marine_transfer_category IN (2, 3)
                ORDER BY b.batch_no ASC
                """,
                [item_code]
            ).fetchall()
            return [dict(r) for r in rows]


def register_batch(
    internal_no: str,
    slip_branch_no: str,
    batch_no: str
) -> dict:
    """Register a batch to an order. Returns status dict."""
    with get_db() as conn:
        # Check lock
        locked = conn.execute(
            "SELECT COUNT(*) as cnt FROM locking_bat WHERE batch_no = ?",
            [batch_no]
        ).fetchone()
        if dict(locked)["cnt"] > 0:
            return {"success": False, "error": "関連バッチが割当済みです。"}

        # Update transfer_order
        conn.execute(
            """
            UPDATE transfer_order
            SET shipping_status = 1, batch_no = ?
            WHERE internal_no = ? AND slip_branch_no = ?
            """,
            [batch_no, internal_no, slip_branch_no]
        )

        # Get flowmeter from batch master
        bat = conn.execute(
            "SELECT flowmeter_name1 FROM m_bat WHERE batch_no = ?",
            [batch_no]
        ).fetchone()
        flowmeter = dict(bat)["flowmeter_name1"] if bat else None

        # Update transfer_record
        conn.execute(
            """
            UPDATE transfer_record
            SET oil1_flowmeter = ?
            WHERE internal_no = ? AND slip_branch_no = ?
            """,
            [flowmeter, internal_no, slip_branch_no]
        )

        # Get order info for locking
        order = conn.execute(
            "SELECT slip_no FROM transfer_order WHERE internal_no = ? AND slip_branch_no = ?",
            [internal_no, slip_branch_no]
        ).fetchone()
        slip_no = dict(order)["slip_no"] if order else ""

        # Register lock
        conn.execute(
            """
            INSERT OR IGNORE INTO locking_bat (batch_no, lock_source_internal_no, lock_source_slip_no, lock_source_slip_branch_no, lock_source_batch_no)
            VALUES (?, ?, ?, ?, ?)
            """,
            [batch_no, internal_no, slip_no, slip_branch_no, batch_no]
        )

        # Lock related batches (batch_flag_tag and batch_lock_no1-10)
        bat_master = conn.execute(
            """
            SELECT batch_flag_tag,
                   batch_lock_no1, batch_lock_no2, batch_lock_no3, batch_lock_no4, batch_lock_no5,
                   batch_lock_no6, batch_lock_no7, batch_lock_no8, batch_lock_no9, batch_lock_no10
            FROM m_bat WHERE batch_no = ?
            """,
            [batch_no]
        ).fetchone()

        if bat_master:
            bm = dict(bat_master)
            # Lock batch_lock_no1-10
            for i in range(1, 11):
                lock_no = bm.get(f"batch_lock_no{i}")
                if lock_no:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO locking_bat (batch_no, lock_source_internal_no, lock_source_slip_no, lock_source_slip_branch_no, lock_source_batch_no)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        [lock_no, internal_no, slip_no, slip_branch_no, batch_no]
                    )

            # Lock same batch_flag_tag batches
            flag_tag = bm.get("batch_flag_tag")
            if flag_tag:
                same_tag_batches = conn.execute(
                    "SELECT batch_no FROM m_bat WHERE batch_flag_tag = ?",
                    [flag_tag]
                ).fetchall()
                for sb in same_tag_batches:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO locking_bat (batch_no, lock_source_internal_no, lock_source_slip_no, lock_source_slip_branch_no, lock_source_batch_no)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        [dict(sb)["batch_no"], internal_no, slip_no, slip_branch_no, batch_no]
                    )

        conn.commit()
        return {"success": True}
