const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

import type { OrdersResponse, BatchesResponse } from "./types";

export async function fetchOrders(params: {
  date_from: string;
  date_to: string;
  slip_no?: string;
  from_tank?: string;
  to_tank?: string;
  item_code?: string;
  item_name?: string;
}): Promise<OrdersResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set("date_from", params.date_from);
  searchParams.set("date_to", params.date_to);
  if (params.slip_no) searchParams.set("slip_no", params.slip_no);
  if (params.from_tank) searchParams.set("from_tank", params.from_tank);
  if (params.to_tank) searchParams.set("to_tank", params.to_tank);
  if (params.item_code) searchParams.set("item_code", params.item_code);
  if (params.item_name) searchParams.set("item_name", params.item_name);

  const res = await fetch(`${BASE_URL}/api/orders?${searchParams.toString()}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "検索に失敗しました。");
  }
  return res.json();
}

export async function fetchAutoRefreshOrders(): Promise<OrdersResponse> {
  const res = await fetch(`${BASE_URL}/api/orders/auto-refresh`);
  if (!res.ok) {
    throw new Error("自動更新に失敗しました。");
  }
  return res.json();
}

export async function fetchBatches(
  internalNo: string,
  slipBranchNo: string
): Promise<BatchesResponse> {
  const res = await fetch(
    `${BASE_URL}/api/orders/${internalNo}/${slipBranchNo}/batches`
  );
  if (!res.ok) {
    throw new Error("バッチ取得に失敗しました。");
  }
  return res.json();
}

export async function registerBatch(
  internalNo: string,
  slipBranchNo: string,
  batchNo: string
): Promise<void> {
  const res = await fetch(
    `${BASE_URL}/api/orders/${internalNo}/${slipBranchNo}/register-batch`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ batch_no: batchNo }),
    }
  );
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "バッチ登録に失敗しました。");
  }
}

export function getExportCsvUrl(params: {
  date_from: string;
  date_to: string;
  slip_no?: string;
  from_tank?: string;
  to_tank?: string;
  item_code?: string;
  item_name?: string;
}): string {
  const searchParams = new URLSearchParams();
  searchParams.set("date_from", params.date_from);
  searchParams.set("date_to", params.date_to);
  if (params.slip_no) searchParams.set("slip_no", params.slip_no);
  if (params.from_tank) searchParams.set("from_tank", params.from_tank);
  if (params.to_tank) searchParams.set("to_tank", params.to_tank);
  if (params.item_code) searchParams.set("item_code", params.item_code);
  if (params.item_name) searchParams.set("item_name", params.item_name);

  return `${BASE_URL}/api/orders/export-csv?${searchParams.toString()}`;
}
