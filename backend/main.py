"""FastAPI backend for 陸上入出荷オーダ一覧画面."""
import csv
import io
import datetime
from typing import Optional

import pathlib

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from database import get_connection, init_db, seed_data

app = FastAPI(title="陸上入出荷オーダ一覧 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()
    seed_data()


# ---------------------------------------------------------------------------
# Helper: build the main query with joins
# ---------------------------------------------------------------------------
_BASE_SELECT = """
SELECT
    lo.internal_no,
    lo.slip_branch_no,
    lo.shipping_date,
    lo.slip_no,
    lo.car_no,
    lo.destination_name,
    lo.min_product_code,
    lo.min_product_name,
    lo.mgmt_product_code,
    lo.mgmt_product_name,
    lo.reservation_qty,
    lo.reservation_unit,
    lo.shipping_type,
    lo.shipping_status,
    lo.ukeharai_kbn,
    lo.ukewatashi_cond,
    lo.trip,
    lo.remarks,
    lr.admission_datetime,
    lr.loading_end_datetime,
    lr.lane_no,
    lr.tank1_1_no,
    lr.result_qty,
    lr.corrected_result_unit,
    lr.corrected_reservation_unit,
    lr.reservation_qty_converted,
    lr.weighing_result,
    lr.result_date,
    ms.abbreviation   AS sts_abbreviation,
    ms.list_order      AS sts_list_order,
    cnp_uke.name_value AS ukeharai_name,
    cnp_uke2.name_value AS ukewatashi_name
FROM land_order lo
LEFT JOIN land_record lr
    ON lo.internal_no = lr.internal_no AND lo.slip_branch_no = lr.slip_branch_no
LEFT JOIN m_shipping_sts ms
    ON ms.status_category = 1
    AND lo.shipping_type = ms.shipping_type
    AND lo.shipping_status = ms.shipping_status
LEFT JOIN m_code_name_pair cnp_uke
    ON cnp_uke.name_type = '11' AND lo.ukeharai_kbn = cnp_uke.name_code
LEFT JOIN m_code_name_pair cnp_uke2
    ON cnp_uke2.name_type = '13' AND lo.ukewatashi_cond = cnp_uke2.name_code
"""


def _build_where(
    date_from: str,
    date_to: str,
    order_statuses: Optional[str],
    car_no: Optional[str],
    tank: Optional[str],
    lane: Optional[str],
    destination: Optional[str],
    min_product_code: Optional[str],
    min_product_name: Optional[str],
    slip_no: Optional[str],
    ukeharai: Optional[str],
    ukewatashi: Optional[str],
    shipping_type: Optional[str],
    sts: Optional[str],
    mgmt_product_code: Optional[str],
    mgmt_product_name: Optional[str],
):
    """Return (where_clause, params) tuple."""
    clauses = []
    params = []

    # Date range
    clauses.append("DATE(lo.shipping_date) >= ?")
    params.append(date_from)
    clauses.append("DATE(lo.shipping_date) <= ?")
    params.append(date_to)

    # Order status filter
    if order_statuses and order_statuses != "all":
        status_list = order_statuses.split(",")
        status_values = []
        for s in status_list:
            if s == "reservation":
                status_values.append(0)
            elif s == "admission":
                status_values.extend([5, 10, 15])
            elif s == "lane_entry":
                status_values.extend([20, 25, 30, 35])
            elif s == "no_result":
                status_values.append(40)
            elif s == "result":
                status_values.append(41)
        if status_values:
            placeholders = ",".join("?" * len(status_values))
            clauses.append(f"lo.shipping_status IN ({placeholders})")
            params.extend(status_values)

    # Text search filters
    if car_no:
        clauses.append("lo.car_no LIKE ?")
        params.append(f"{car_no}%")
    if tank:
        clauses.append("""(
            lr.tank1_1_no = ? OR lr.tank1_2_no = ? OR lr.tank1_3_no = ?
            OR lr.tank2_1_no = ? OR lr.tank2_2_no = ? OR lr.tank2_3_no = ?
        )""")
        params.extend([tank] * 6)
    if lane:
        clauses.append("lr.lane_no = ?")
        params.append(int(lane))
    if destination:
        clauses.append("lo.destination_name LIKE ?")
        params.append(f"%{destination}%")
    if min_product_code:
        clauses.append("lo.min_product_code LIKE ?")
        params.append(f"{min_product_code}%")
    if min_product_name:
        clauses.append("lo.min_product_name LIKE ?")
        params.append(f"%{min_product_name}%")
    if slip_no:
        clauses.append("lo.slip_no LIKE ?")
        params.append(f"{slip_no}%")
    if ukeharai:
        clauses.append("lo.ukeharai_kbn = ?")
        params.append(ukeharai)
    if ukewatashi:
        clauses.append("lo.ukewatashi_cond = ?")
        params.append(ukewatashi)
    if shipping_type:
        clauses.append("lo.shipping_type = ?")
        params.append(shipping_type)
    if sts is not None and sts != "":
        clauses.append("lo.shipping_status = ?")
        params.append(int(sts))
    if mgmt_product_code:
        clauses.append("lo.mgmt_product_code LIKE ?")
        params.append(f"{mgmt_product_code}%")
    if mgmt_product_name:
        clauses.append("lo.mgmt_product_name LIKE ?")
        params.append(f"%{mgmt_product_name}%")

    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    return where, params


_ORDER_BY = " ORDER BY COALESCE(ms.list_order, 9999), lo.internal_no, lo.slip_branch_no"


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/orders")
def search_orders(
    date_from: str = Query(...),
    date_to: str = Query(...),
    order_statuses: Optional[str] = Query(None),
    car_no: Optional[str] = Query(None),
    tank: Optional[str] = Query(None),
    lane: Optional[str] = Query(None),
    destination: Optional[str] = Query(None),
    min_product_code: Optional[str] = Query(None),
    min_product_name: Optional[str] = Query(None),
    slip_no: Optional[str] = Query(None),
    ukeharai: Optional[str] = Query(None),
    ukewatashi: Optional[str] = Query(None),
    shipping_type: Optional[str] = Query(None),
    sts: Optional[str] = Query(None),
    mgmt_product_code: Optional[str] = Query(None),
    mgmt_product_name: Optional[str] = Query(None),
):
    where, params = _build_where(
        date_from, date_to, order_statuses,
        car_no, tank, lane, destination,
        min_product_code, min_product_name, slip_no,
        ukeharai, ukewatashi, shipping_type, sts,
        mgmt_product_code, mgmt_product_name,
    )
    conn = get_connection()
    sql = _BASE_SELECT + where + _ORDER_BY
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    now_str = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    result = []
    for r in rows:
        row_dict = dict(r)
        # Format admission time (hh:mm)
        adm = row_dict.get("admission_datetime") or ""
        if adm and " " in adm:
            adm = adm.split(" ")[1][:5]
        row_dict["admission_time"] = adm

        # Format loading end time (hh:mm)
        end = row_dict.get("loading_end_datetime") or ""
        if end and " " in end:
            end = end.split(" ")[1][:5]
        row_dict["loading_end_time"] = end

        # Reservation qty + unit display
        res_qty = row_dict.get("reservation_qty")
        res_unit = row_dict.get("reservation_unit")
        res_qty_conv = row_dict.get("reservation_qty_converted")
        if res_unit == "10":
            row_dict["reservation_qty_display"] = str(int(res_qty)) if res_qty is not None else ""
            row_dict["reservation_unit_display"] = "kg"
        elif res_unit == "20":
            row_dict["reservation_qty_display"] = str(int(res_qty * 1000)) if res_qty is not None else ""
            row_dict["reservation_unit_display"] = "kg"
        else:
            if res_qty_conv is not None:
                row_dict["reservation_qty_display"] = f"{res_qty_conv:.3f}"
            elif res_qty is not None:
                row_dict["reservation_qty_display"] = f"{res_qty:.3f}"
            else:
                row_dict["reservation_qty_display"] = ""
            row_dict["reservation_unit_display"] = "kL"

        # Result qty + unit display
        result_qty = row_dict.get("result_qty")
        corr_unit = row_dict.get("corrected_result_unit")
        if result_qty is not None:
            if corr_unit == "01" or corr_unit == "10":
                row_dict["result_qty_display"] = str(int(result_qty))
                row_dict["result_unit_display"] = "kg"
            else:
                row_dict["result_qty_display"] = f"{result_qty:.3f}"
                row_dict["result_unit_display"] = "kL"
        else:
            row_dict["result_qty_display"] = ""
            row_dict["result_unit_display"] = ""

        # Slip No display (No-枝番)
        sn = row_dict.get("slip_no") or ""
        sb = row_dict.get("slip_branch_no") or ""
        row_dict["slip_no_display"] = f"{sn}-{sb}" if sn else ""

        result.append(row_dict)

    return {"timestamp": now_str, "count": len(result), "data": result}


@app.get("/api/orders/csv")
def export_csv(
    date_from: str = Query(...),
    date_to: str = Query(...),
    order_statuses: Optional[str] = Query(None),
    car_no: Optional[str] = Query(None),
    tank: Optional[str] = Query(None),
    lane: Optional[str] = Query(None),
    destination: Optional[str] = Query(None),
    min_product_code: Optional[str] = Query(None),
    min_product_name: Optional[str] = Query(None),
    slip_no: Optional[str] = Query(None),
    ukeharai: Optional[str] = Query(None),
    ukewatashi: Optional[str] = Query(None),
    shipping_type: Optional[str] = Query(None),
    sts: Optional[str] = Query(None),
    mgmt_product_code: Optional[str] = Query(None),
    mgmt_product_name: Optional[str] = Query(None),
):
    """Re-search and export results as CSV."""
    where, params = _build_where(
        date_from, date_to, order_statuses,
        car_no, tank, lane, destination,
        min_product_code, min_product_name, slip_no,
        ukeharai, ukewatashi, shipping_type, sts,
        mgmt_product_code, mgmt_product_name,
    )
    conn = get_connection()
    sql = _BASE_SELECT + where + _ORDER_BY
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    if len(rows) == 0:
        return {"error": "検索結果が0件でした。"}

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    headers = [
        "入門", "終了", "レーン", "STS", "車番", "届け先名",
        "最小品名コード", "最小品名", "タンク", "予約数量",
        "実績数量", "形態", "計量値", "Trip", "伝票No",
        "管理品名コード", "管理品名", "受払", "受渡", "備考", "実績日",
    ]
    writer.writerow(headers)

    for r in rows:
        rd = dict(r)
        # admission datetime formatted
        adm = rd.get("admission_datetime") or ""
        if adm:
            adm = adm.replace("-", "/")
            if len(adm) > 16:
                adm = adm[:16]

        end = rd.get("loading_end_datetime") or ""
        if end:
            end = end.replace("-", "/")
            if len(end) > 16:
                end = end[:16]

        # Reservation qty
        res_qty = rd.get("reservation_qty")
        res_unit = rd.get("reservation_unit")
        res_qty_conv = rd.get("reservation_qty_converted")
        if res_unit == "10":
            rq_disp = f"{int(res_qty)}kg" if res_qty is not None else ""
        elif res_unit == "20":
            rq_disp = f"{int(res_qty * 1000)}kg" if res_qty is not None else ""
        else:
            if res_qty_conv is not None:
                rq_disp = f"{res_qty_conv:.3f}kL"
            elif res_qty is not None:
                rq_disp = f"{res_qty:.3f}kL"
            else:
                rq_disp = ""

        # Result qty
        result_qty = rd.get("result_qty")
        corr_unit = rd.get("corrected_result_unit")
        if result_qty is not None:
            if corr_unit == "01" or corr_unit == "10":
                rr_disp = f"{int(result_qty)}kg"
            else:
                rr_disp = f"{result_qty:.3f}kL"
        else:
            rr_disp = ""

        sn = rd.get("slip_no") or ""
        sb = rd.get("slip_branch_no") or ""
        slip_disp = f"{sn}-{sb}" if sn else ""

        writer.writerow([
            adm, end,
            rd.get("lane_no") or "",
            rd.get("sts_abbreviation") or "",
            rd.get("car_no") or "",
            rd.get("destination_name") or "",
            rd.get("min_product_code") or "",
            rd.get("min_product_name") or "",
            rd.get("tank1_1_no") or "",
            rq_disp,
            rr_disp,
            rd.get("shipping_type") or "",
            rd.get("weighing_result") or "",
            rd.get("trip") or "",
            slip_disp,
            rd.get("mgmt_product_code") or "",
            rd.get("mgmt_product_name") or "",
            rd.get("ukeharai_kbn") or "",
            rd.get("ukewatashi_cond") or "",
            rd.get("remarks") or "",
            rd.get("result_date") or "",
        ])

    now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"land_order_{now}.csv"

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/api/master/shipping_sts")
def get_shipping_sts():
    """Get shipping status master for dropdown."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT DISTINCT shipping_status, abbreviation, list_order
        FROM m_shipping_sts
        WHERE status_category = 1
        ORDER BY shipping_type, shipping_status
    """).fetchall()
    conn.close()
    # De-duplicate by shipping_status
    seen = set()
    result = []
    for r in rows:
        if r["shipping_status"] not in seen:
            seen.add(r["shipping_status"])
            result.append({
                "shipping_status": r["shipping_status"],
                "abbreviation": r["abbreviation"],
                "list_order": r["list_order"],
            })
    result.sort(key=lambda x: x["list_order"] or 999)
    return result


@app.get("/api/master/code_names/{name_type}")
def get_code_names(name_type: str):
    """Get code-name pairs for dropdowns."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT name_code, name_value FROM m_code_name_pair WHERE name_type = ? ORDER BY name_code",
        (name_type,),
    ).fetchall()
    conn.close()
    return [{"code": r["name_code"], "name": r["name_value"]} for r in rows]


@app.post("/api/order_receive")
def order_receive(date_from: str = Query(...), date_to: str = Query(...)):
    """Dummy: オーダ受信処理."""
    # TODO: 実際のオーダ受信処理（外部連携）はダミー
    return {"message": "オーダ受信処理を実行しました（ダミー）", "date_from": date_from, "date_to": date_to}


@app.post("/api/card/car")
def issue_car_card(internal_no: str = Query(...), slip_branch_no: str = Query(...)):
    """Dummy: 車番カード発行."""
    # TODO: 実際の車番カード発行処理はダミー
    return {"message": "車番カードを発行しました（ダミー）"}


@app.post("/api/card/order")
def issue_order_card(internal_no: str = Query(...), slip_branch_no: str = Query(...)):
    """Dummy: オーダカード発行."""
    # TODO: 実際のオーダカード発行処理はダミー
    return {"message": "オーダカードを発行しました（ダミー）"}


@app.post("/api/admission")
def admission_accept(internal_no: str = Query(...), slip_branch_no: str = Query(...)):
    """Dummy: 入門受付処理."""
    # TODO: 実際の入門受付処理はダミー。仮DB更新のみ。
    conn = get_connection()
    conn.execute(
        "UPDATE land_order SET shipping_status = 5 WHERE internal_no = ? AND slip_branch_no = ?",
        (internal_no, slip_branch_no),
    )
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    conn.execute(
        "INSERT INTO land_record (internal_no, slip_branch_no, admission_datetime) VALUES (?, ?, ?) "
        "ON CONFLICT(internal_no, slip_branch_no) DO UPDATE SET admission_datetime = excluded.admission_datetime",
        (internal_no, slip_branch_no, now),
    )
    conn.commit()
    conn.close()
    return {"message": "入門受付を行いました（ダミー）"}


@app.post("/api/admission/cancel")
def admission_cancel(internal_no: str = Query(...), slip_branch_no: str = Query(...)):
    """Dummy: 受付キャンセル処理."""
    # TODO: 実際の受付キャンセル処理はダミー。仮DB更新のみ。
    conn = get_connection()
    conn.execute(
        "UPDATE land_order SET shipping_status = 0 WHERE internal_no = ? AND slip_branch_no = ?",
        (internal_no, slip_branch_no),
    )
    conn.commit()
    conn.close()
    return {"message": "受付キャンセルを行いました（ダミー）"}


@app.post("/api/lane_entry")
def lane_entry(
    internal_no: str = Query(...),
    slip_branch_no: str = Query(...),
    lane_no: int = Query(...),
):
    """Dummy: レーン入線処理."""
    # TODO: 実際のレーン入線処理はダミー。仮DB更新のみ。
    conn = get_connection()
    conn.execute(
        "UPDATE land_order SET shipping_status = 20 WHERE internal_no = ? AND slip_branch_no = ?",
        (internal_no, slip_branch_no),
    )
    conn.execute(
        "UPDATE land_record SET lane_no = ? WHERE internal_no = ? AND slip_branch_no = ?",
        (lane_no, internal_no, slip_branch_no),
    )
    conn.commit()
    conn.close()
    return {"message": f"レーン{lane_no}に入線しました（ダミー）"}


@app.post("/api/weighing")
def weighing_accept(internal_no: str = Query(...), slip_branch_no: str = Query(...)):
    """Dummy: 計量受付処理."""
    # TODO: 実際の計量受付処理はダミー
    return {"message": "計量受付を行いました（ダミー）"}


# ---------------------------------------------------------------------------
# Serve frontend
# ---------------------------------------------------------------------------
_FRONTEND_DIR = pathlib.Path(__file__).resolve().parent.parent / "frontend"


@app.get("/")
def serve_frontend():
    """Serve the frontend index.html."""
    return FileResponse(_FRONTEND_DIR / "index.html", media_type="text/html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
