"""Repository functions for querying SQL Server dbo.TransferOrderList."""

import logging
from typing import Optional
from decimal import Decimal

from app.sqlserver_db import get_sqlserver_db

logger = logging.getLogger(__name__)

# STS text -> shipping_status numeric mapping
STS_TO_STATUS: dict[str, int] = {
    "予約": 0,
    "割当": 1,
    "DCS送": 5,
    "DCS再": 15,
    "移送中": 20,
    "一停": 26,
    "実保": 40,
    "完了": 41,
}

# STS text -> list_order for sorting
STS_TO_LIST_ORDER: dict[str, int] = {
    "予約": 1,
    "割当": 2,
    "DCS送": 3,
    "DCS再": 4,
    "移送中": 5,
    "一停": 6,
    "実保": 7,
    "完了": 8,
}


def _decimal_to_float(val: Decimal | float | int | None) -> float | None:
    """Convert Decimal to float for JSON serialization."""
    if val is None:
        return None
    return float(val)


def _format_datetime(val: object) -> str | None:
    """Format datetime to string."""
    if val is None:
        return None
    return str(val).replace("-", "/")


def _parse_slip_no(slip_no: str | None) -> tuple[str, str]:
    """Parse SlipNo like 'T10001-01' into (slip_no, slip_branch_no)."""
    if not slip_no:
        return ("", "")
    if "-" in slip_no:
        parts = slip_no.rsplit("-", 1)
        return (parts[0], parts[1])
    return (slip_no, "01")


def _row_to_order(row: dict) -> dict:
    """Convert a SQL Server row to the frontend-expected order dict."""
    sts_text = row.get("STS") or ""
    shipping_status = STS_TO_STATUS.get(sts_text, -1)
    list_order = STS_TO_LIST_ORDER.get(sts_text, 999)
    slip_no_raw = row.get("SlipNo") or ""
    slip_no, slip_branch_no = _parse_slip_no(slip_no_raw)

    return {
        "internal_no": str(row.get("Id", "")),
        "slip_branch_no": slip_branch_no,
        "transfer_date": None,
        "slip_no": slip_no,
        "from_tank_no": row.get("FromTank") or "",
        "to_tank_no": row.get("ToTank") or "",
        "item_code": "",
        "item_name": row.get("ProductName") or "",
        "shipping_status": shipping_status,
        "batch_no": None,
        "status_abbreviation": sts_text,
        "status_list_order": list_order,
        "plan_quantity_net": _decimal_to_float(row.get("PlannedNet")),
        "actual_net": _decimal_to_float(row.get("ActualNet")),
        "actual_gross": _decimal_to_float(row.get("ActualGross")),
        "transfer_start_datetime": _format_datetime(row.get("StartDateTime")),
        "transfer_end_datetime": _format_datetime(row.get("EndDateTime")),
        "modified_reserve_unit_code": "01",
        "unit_name": "kL",
        "batch_name": None,
    }


def search_transfer_orders_sqlserver(
    slip_no: Optional[str] = None,
    from_tank: Optional[str] = None,
    to_tank: Optional[str] = None,
    item_name: Optional[str] = None,
) -> list[dict]:
    """Search transfer orders from SQL Server dbo.TransferOrderList.

    Note: date_from/date_to are ignored since the table has no transfer_date column.
    All records are returned and optionally filtered by search conditions.
    """
    try:
        with get_sqlserver_db() as conn:
            cursor = conn.cursor(as_dict=True)

            query = "SELECT Id, STS, FromTank, ToTank, ProductName, PlannedNet, ActualNet, ActualGross, SlipNo, StartDateTime, EndDateTime FROM dbo.TransferOrderList WHERE 1=1"
            params: list = []

            if slip_no:
                query += " AND SlipNo LIKE %s"
                params.append(f"{slip_no}%")
            if from_tank:
                query += " AND FromTank = %s"
                params.append(from_tank)
            if to_tank:
                query += " AND ToTank = %s"
                params.append(to_tank)
            if item_name:
                query += " AND ProductName LIKE %s"
                params.append(f"%{item_name}%")

            query += " ORDER BY Id ASC"

            cursor.execute(query, tuple(params) if params else None)
            rows = cursor.fetchall()

            orders = [_row_to_order(row) for row in rows]
            # Sort by status list_order then Id
            orders.sort(key=lambda x: (x.get("status_list_order") or 999, x["internal_no"]))
            return orders

    except Exception as e:
        logger.error("SQL Server query error: %s", e)
        raise


def search_auto_refresh_orders_sqlserver() -> list[dict]:
    """Auto-refresh: return all records from SQL Server (no date filter available)."""
    return search_transfer_orders_sqlserver()
