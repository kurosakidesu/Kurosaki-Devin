from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import datetime
import logging
import os

from dotenv import load_dotenv
load_dotenv()

from app.database import init_db, seed_db
from app.repository import (
    get_assignable_batches,
    register_batch,
)
from app.sqlserver_repository import (
    search_transfer_orders_sqlserver,
    search_auto_refresh_orders_sqlserver,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI()

# Disable CORS. Do not remove this for full-stack development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


@app.on_event("startup")
def startup():
    init_db()
    seed_db()


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/api/orders")
async def get_orders(
    date_from: str = Query(..., description="yyyy-mm-dd"),
    date_to: str = Query(..., description="yyyy-mm-dd"),
    slip_no: Optional[str] = Query(None),
    from_tank: Optional[str] = Query(None),
    to_tank: Optional[str] = Query(None),
    item_code: Optional[str] = Query(None),
    item_name: Optional[str] = Query(None),
):
    """Search transfer orders based on conditions."""
    try:
        df = datetime.date.fromisoformat(date_from)
        dt = datetime.date.fromisoformat(date_to)
    except ValueError:
        raise HTTPException(status_code=400, detail="日付の形式が不正です。")

    if df > dt:
        raise HTTPException(
            status_code=400,
            detail="移送日_Fromは移送日_To以前の日付を入力してください。",
        )

    try:
        rows = search_transfer_orders_sqlserver(
            slip_no=slip_no or None,
            from_tank=from_tank or None,
            to_tank=to_tank or None,
            item_name=item_name or None,
        )
    except Exception as e:
        logger.error("SQL Server query failed: %s", e)
        raise HTTPException(status_code=500, detail=f"DB接続エラー: {e}")

    return {
        "data": rows,
        "count": len(rows),
        "searched_at": datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
    }


@app.get("/api/orders/auto-refresh")
async def get_orders_auto_refresh():
    """Auto-refresh: all records from SQL Server."""
    try:
        rows = search_auto_refresh_orders_sqlserver()
    except Exception as e:
        logger.error("SQL Server auto-refresh query failed: %s", e)
        raise HTTPException(status_code=500, detail=f"DB接続エラー: {e}")

    return {
        "data": rows,
        "count": len(rows),
        "searched_at": datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
    }


@app.get("/api/orders/{internal_no}/{slip_branch_no}/batches")
async def get_batches(internal_no: str, slip_branch_no: str):
    """Get assignable batches for a given order."""
    batches = get_assignable_batches(internal_no, slip_branch_no)
    return {"data": batches, "count": len(batches)}


class RegisterBatchRequest(BaseModel):
    batch_no: str


@app.post("/api/orders/{internal_no}/{slip_branch_no}/register-batch")
async def register_batch_endpoint(
    internal_no: str,
    slip_branch_no: str,
    body: RegisterBatchRequest,
):
    """Register a batch to the selected order."""
    result = register_batch(internal_no, slip_branch_no, body.batch_no)
    if not result["success"]:
        raise HTTPException(status_code=409, detail=result["error"])
    return {"success": True, "message": "バッチを登録しました。"}


@app.get("/api/orders/export-csv")
async def export_csv(
    date_from: str = Query(...),
    date_to: str = Query(...),
    slip_no: Optional[str] = Query(None),
    from_tank: Optional[str] = Query(None),
    to_tank: Optional[str] = Query(None),
    item_code: Optional[str] = Query(None),
    item_name: Optional[str] = Query(None),
):
    """Export search results as CSV."""
    import csv
    import io
    from fastapi.responses import StreamingResponse

    try:
        df = datetime.date.fromisoformat(date_from)
        dt = datetime.date.fromisoformat(date_to)
    except ValueError:
        raise HTTPException(status_code=400, detail="日付の形式が不正です。")

    if df > dt:
        raise HTTPException(
            status_code=400,
            detail="移送日_Fromは移送日_To以前の日付を入力してください。",
        )

    try:
        rows = search_transfer_orders_sqlserver(
            slip_no=slip_no or None,
            from_tank=from_tank or None,
            to_tank=to_tank or None,
            item_name=item_name or None,
        )
    except Exception as e:
        logger.error("SQL Server CSV export query failed: %s", e)
        raise HTTPException(status_code=500, detail=f"DB接続エラー: {e}")

    if len(rows) == 0:
        raise HTTPException(status_code=404, detail="検索結果が0件でした。")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "STS", "From_タンク", "To_タンク", "管理品名コード", "管理品名",
        "計画量_Net", "実績量_Net", "実績量_Gross", "単位", "伝票No",
        "開始日時", "終了日時"
    ])
    for r in rows:
        plan_net = f"{r['plan_quantity_net']:.3f}" if r.get("plan_quantity_net") is not None else ""
        actual_net_val = r.get("actual_net")
        actual_net = f"{actual_net_val:.3f}" if actual_net_val is not None and actual_net_val != 0 else ""
        actual_gross_val = r.get("actual_gross")
        actual_gross = f"{actual_gross_val:.3f}" if actual_gross_val is not None and actual_gross_val != 0 else ""
        slip_display = f"{r.get('slip_no', '')}-{r.get('slip_branch_no', '')}"
        writer.writerow([
            r.get("status_abbreviation", ""),
            r.get("from_tank_no", ""),
            r.get("to_tank_no", ""),
            r.get("item_code", ""),
            r.get("item_name", ""),
            plan_net,
            actual_net,
            actual_gross,
            "kL",
            slip_display,
            r.get("transfer_start_datetime", "") or "",
            r.get("transfer_end_datetime", "") or "",
        ])

    output.seek(0)
    now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"transfer_order_{now}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
