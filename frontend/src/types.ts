export interface TransferOrder {
  internal_no: string;
  slip_branch_no: string;
  transfer_date: string;
  slip_no: string;
  from_tank_no: string;
  to_tank_no: string;
  item_code: string;
  item_name: string;
  shipping_status: number;
  batch_no: string | null;
  status_abbreviation: string | null;
  status_list_order: number | null;
  plan_quantity_net: number | null;
  actual_net: number | null;
  actual_gross: number | null;
  transfer_start_datetime: string | null;
  transfer_end_datetime: string | null;
  modified_reserve_unit_code: string | null;
  unit_name: string | null;
  batch_name: string | null;
}

export interface BatchInfo {
  batch_no: string;
  batch_name: string;
}

export interface OrdersResponse {
  data: TransferOrder[];
  count: number;
  searched_at: string;
}

export interface BatchesResponse {
  data: BatchInfo[];
  count: number;
}
