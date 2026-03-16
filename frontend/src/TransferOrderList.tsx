import { useState, useEffect, useCallback, useRef } from "react";
import type { TransferOrder, BatchInfo } from "./types";
import {
  fetchOrders,
  fetchAutoRefreshOrders,
  fetchBatches,
  registerBatch,
  getExportCsvUrl,
} from "./api";

function formatDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function formatNumber3(val: number | null | undefined): string {
  if (val === null || val === undefined) return "";
  if (val === 0) return "0.000";
  return val.toFixed(3);
}

function formatDatetime(val: string | null | undefined): string {
  if (!val) return "";
  // Expect "yyyy-mm-dd HH:MM" or similar
  return val.replace(/-/g, "/").substring(0, 16);
}

/** Row background color based on shipping status */
function getRowBgColor(status: number): string {
  // 移送中: 5, 15, 20, 26, 40 -> light red
  if ([5, 15, 20, 26, 40].includes(status)) return "#ffcccc";
  // バッチ割当: 1 -> yellow
  if (status === 1) return "#ffffcc";
  // 予約: 0 -> white
  if (status === 0) return "#ffffff";
  // 完了: 41 -> light green
  if (status === 41) return "#ccffcc";
  return "#ffffff";
}

const AUTO_REFRESH_INTERVAL = 15000; // 15 seconds

export default function TransferOrderList() {
  // Date search conditions
  const today = new Date();
  const [dateFrom, setDateFrom] = useState(formatDate(today));
  const [dateTo, setDateTo] = useState(formatDate(today));

  // Additional search conditions
  const [showSearchConditions, setShowSearchConditions] = useState(false);
  const [slipNo, setSlipNo] = useState("");
  const [fromTank, setFromTank] = useState("");
  const [toTank, setToTank] = useState("");
  const [itemCode, setItemCode] = useState("");
  const [itemName, setItemName] = useState("");

  // Order list
  const [orders, setOrders] = useState<TransferOrder[]>([]);
  const [searchedAt, setSearchedAt] = useState("");
  const [selectedOrderKey, setSelectedOrderKey] = useState<string | null>(null);

  // Batch selection
  const [batchList, setBatchList] = useState<BatchInfo[]>([]);
  const [selectedBatchNo, setSelectedBatchNo] = useState("");

  // Auto refresh
  const [autoRefresh, setAutoRefresh] = useState(true);
  const autoRefreshRef = useRef(autoRefresh);
  autoRefreshRef.current = autoRefresh;
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Error message
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Loading
  const [loading, setLoading] = useState(false);

  const selectedOrder = orders.find(
    (o) => `${o.internal_no}-${o.slip_branch_no}` === selectedOrderKey
  );

  // --- Search ---
  const doSearch = useCallback(
    async (params?: {
      dateFrom?: string;
      dateTo?: string;
      slipNo?: string;
      fromTank?: string;
      toTank?: string;
      itemCode?: string;
      itemName?: string;
    }) => {
      const df = params?.dateFrom ?? dateFrom;
      const dt = params?.dateTo ?? dateTo;
      const sn = params?.slipNo ?? slipNo;
      const ft = params?.fromTank ?? fromTank;
      const tt = params?.toTank ?? toTank;
      const ic = params?.itemCode ?? itemCode;
      const inm = params?.itemName ?? itemName;

      setLoading(true);
      setErrorMsg(null);
      try {
        const result = await fetchOrders({
          date_from: df,
          date_to: dt,
          slip_no: sn || undefined,
          from_tank: ft || undefined,
          to_tank: tt || undefined,
          item_code: ic || undefined,
          item_name: inm || undefined,
        });
        setOrders(result.data);
        setSearchedAt(result.searched_at);
        setSelectedOrderKey(null);
        setBatchList([]);
        setSelectedBatchNo("");
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : "検索に失敗しました。";
        setErrorMsg(msg);
      } finally {
        setLoading(false);
      }
    },
    [dateFrom, dateTo, slipNo, fromTank, toTank, itemCode, itemName]
  );

  // --- Auto refresh ---
  const doAutoRefresh = useCallback(async () => {
    if (!autoRefreshRef.current) return;
    try {
      const result = await fetchAutoRefreshOrders();
      setOrders(result.data);
      setSearchedAt(result.searched_at);
    } catch {
      // Silently ignore auto-refresh errors
    }
  }, []);

  useEffect(() => {
    // Initial load
    doAutoRefresh();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (autoRefresh) {
      timerRef.current = setInterval(() => {
        doAutoRefresh();
      }, AUTO_REFRESH_INTERVAL);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [autoRefresh, doAutoRefresh]);

  // When search conditions change, stop auto-refresh
  const handleSearchConditionChange = useCallback(() => {
    setAutoRefresh(false);
  }, []);

  // --- Date navigation ---
  const handlePrevDay = () => {
    const df = new Date(dateFrom);
    const dt = new Date(dateTo);
    df.setDate(df.getDate() - 1);
    dt.setDate(dt.getDate() - 1);
    const newFrom = formatDate(df);
    const newTo = formatDate(dt);
    setDateFrom(newFrom);
    setDateTo(newTo);
    doSearch({ dateFrom: newFrom, dateTo: newTo });
  };

  const handleToday = () => {
    const t = formatDate(new Date());
    setDateFrom(t);
    setDateTo(t);
    doSearch({ dateFrom: t, dateTo: t });
  };

  const handleNextDay = () => {
    const df = new Date(dateFrom);
    const dt = new Date(dateTo);
    df.setDate(df.getDate() + 1);
    dt.setDate(dt.getDate() + 1);
    const newFrom = formatDate(df);
    const newTo = formatDate(dt);
    setDateFrom(newFrom);
    setDateTo(newTo);
    doSearch({ dateFrom: newFrom, dateTo: newTo });
  };

  // --- Display button ---
  const handleDisplay = () => {
    if (!dateFrom || !dateTo) {
      setErrorMsg("移送日は正しい日付を入力してください。");
      return;
    }
    if (dateFrom > dateTo) {
      setErrorMsg("移送日_Fromは移送日_To以前の日付を入力してください。");
      return;
    }
    doSearch();
  };

  // --- Clear button ---
  const handleClear = () => {
    const t = formatDate(new Date());
    setDateFrom(t);
    setDateTo(t);
    setSlipNo("");
    setFromTank("");
    setToTank("");
    setItemCode("");
    setItemName("");
    setSelectedOrderKey(null);
    setBatchList([]);
    setSelectedBatchNo("");
    setErrorMsg(null);
  };

  // --- File export ---
  const handleFileExport = () => {
    if (!dateFrom || !dateTo) {
      setErrorMsg("移送日は正しい日付を入力してください。");
      return;
    }
    const ok = window.confirm("入力された条件で再検索してファイル出力します。");
    if (!ok) return;

    const url = getExportCsvUrl({
      date_from: dateFrom,
      date_to: dateTo,
      slip_no: slipNo || undefined,
      from_tank: fromTank || undefined,
      to_tank: toTank || undefined,
      item_code: itemCode || undefined,
      item_name: itemName || undefined,
    });
    window.open(url, "_blank");
  };

  // --- Order receive (dummy) ---
  const handleOrderReceive = () => {
    if (!dateFrom || !dateTo) {
      setErrorMsg("移送日は正しい日付を入力してください。");
      return;
    }
    if (dateFrom > dateTo) {
      setErrorMsg("移送日_Fromは移送日_To以前の日付を入力してください。");
      return;
    }
    const ok = window.confirm("オーダ受信を行います。");
    if (!ok) return;

    // TODO: Call external TransferReceiveOrder.exe (dummy)
    alert("オーダ受信処理はダミーです。（外部連携は未実装）");

    // Clear search conditions except dates, stop auto refresh, re-search
    setSlipNo("");
    setFromTank("");
    setToTank("");
    setItemCode("");
    setItemName("");
    setAutoRefresh(false);
    doSearch({ slipNo: "", fromTank: "", toTank: "", itemCode: "", itemName: "" });
  };

  // --- Auto refresh toggle ---
  const handleAutoRefreshToggle = () => {
    if (autoRefresh) {
      // Currently auto-refreshing -> stop
      setAutoRefresh(false);
    } else {
      // Currently stopped -> start
      const t = formatDate(new Date());
      setDateFrom(t);
      setDateTo(t);
      setSlipNo("");
      setFromTank("");
      setToTank("");
      setItemCode("");
      setItemName("");
      setAutoRefresh(true);
    }
  };

  // --- Order row click ---
  const handleOrderClick = async (order: TransferOrder) => {
    const key = `${order.internal_no}-${order.slip_branch_no}`;
    setSelectedOrderKey(key);
    setSelectedBatchNo("");

    try {
      const result = await fetchBatches(
        order.internal_no,
        order.slip_branch_no
      );
      setBatchList(result.data);
    } catch {
      setBatchList([]);
    }
  };

  // --- Order row double click ---
  const handleOrderDoubleClick = (order: TransferOrder) => {
    // TODO: Navigate to 移送油量実績画面 with internal_no and slip_branch_no
    alert(
      `移送油量実績画面へ遷移（ダミー）\n内部管理No: ${order.internal_no}\n伝票枝番: ${order.slip_branch_no}`
    );
  };

  // --- Register batch ---
  const handleRegister = async () => {
    if (!selectedOrder) {
      setErrorMsg("オーダを選択してください。");
      return;
    }
    if (!selectedBatchNo) {
      setErrorMsg("バッチNoの選択は必須です。");
      return;
    }

    const selectedBatch = batchList.find((b) => b.batch_no === selectedBatchNo);
    const batchDisplay = selectedBatch
      ? `${selectedBatch.batch_no} ${selectedBatch.batch_name}`
      : selectedBatchNo;
    const slipDisplay = `${selectedOrder.slip_no}-${selectedOrder.slip_branch_no}`;

    const ok = window.confirm(
      `伝票No ${slipDisplay} のオーダにバッチ ${batchDisplay} を登録します。`
    );
    if (!ok) return;

    try {
      await registerBatch(
        selectedOrder.internal_no,
        selectedOrder.slip_branch_no,
        selectedBatchNo
      );
      // Re-search to reflect changes
      doSearch();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "バッチ割当に失敗しました。";
      setErrorMsg(msg);
    }
  };

  // --- Navigate to batch setting screen (dummy) ---
  const handleBatchSetting = () => {
    if (!selectedOrder) return;
    // TODO: Navigate to 移送バッチ設定画面
    alert(
      `移送バッチ設定画面へ遷移（ダミー）\n内部管理No: ${selectedOrder.internal_no}\n伝票枝番: ${selectedOrder.slip_branch_no}`
    );
  };

  // Determine button label for register/setting
  const getRegisterButtonLabel = (): string | null => {
    if (!selectedOrder) return null;
    if (selectedOrder.batch_no) return "設定/状況";
    return "登録";
  };

  const isRegisterDisabled = (): boolean => {
    if (!selectedOrder) return true;
    const label = getRegisterButtonLabel();
    if (label === "登録") {
      // Disabled if status is not 0 (予約) or no assignable batches
      if (selectedOrder.shipping_status !== 0) return true;
      if (batchList.length === 0) return true;
      return false;
    }
    return false; // 設定/状況 is always enabled
  };

  return (
    <div
      style={{
        fontFamily: "'Meiryo', 'MS Gothic', sans-serif",
        fontSize: "12px",
        padding: "8px",
        backgroundColor: "#f0f0f0",
        minHeight: "100vh",
      }}
    >
      {/* Header */}
      <div
        style={{
          backgroundColor: "#336699",
          color: "white",
          padding: "6px 12px",
          fontWeight: "bold",
          fontSize: "14px",
          marginBottom: "4px",
        }}
      >
        移送オーダ一覧画面
      </div>

      {/* Error message */}
      {errorMsg && (
        <div
          style={{
            backgroundColor: "#ffcccc",
            border: "1px solid #cc0000",
            padding: "6px 12px",
            marginBottom: "4px",
            color: "#cc0000",
          }}
        >
          {errorMsg}
          <button
            onClick={() => setErrorMsg(null)}
            style={{ marginLeft: "12px", cursor: "pointer" }}
          >
            OK
          </button>
        </div>
      )}

      {/* Date selector row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "6px",
          marginBottom: "4px",
          flexWrap: "wrap",
          backgroundColor: "#e8e8e8",
          padding: "6px",
          border: "1px solid #ccc",
        }}
      >
        <span style={{ fontWeight: "bold" }}>移送日</span>
        <input
          type="date"
          value={dateFrom}
          onChange={(e) => {
            setDateFrom(e.target.value);
            handleSearchConditionChange();
          }}
          style={{ padding: "2px 4px", fontSize: "12px" }}
        />
        <span>～</span>
        <input
          type="date"
          value={dateTo}
          onChange={(e) => {
            setDateTo(e.target.value);
            handleSearchConditionChange();
          }}
          style={{ padding: "2px 4px", fontSize: "12px" }}
        />
        <button onClick={handlePrevDay} style={btnStyle}>
          ＜前日
        </button>
        <button onClick={handleToday} style={btnStyle}>
          今日
        </button>
        <button onClick={handleNextDay} style={btnStyle}>
          翌日＞
        </button>

        <div style={{ flex: 1 }} />

        <button onClick={handleDisplay} style={btnStylePrimary}>
          表示
        </button>
        <button onClick={handleClear} style={btnStyle}>
          クリア
        </button>
        <button onClick={handleFileExport} style={btnStyle}>
          ファイル出力
        </button>
        <button onClick={handleOrderReceive} style={btnStyle}>
          オーダ受信
        </button>
        <button
          onClick={handleAutoRefreshToggle}
          style={{
            ...btnStyle,
            backgroundColor: autoRefresh ? "#339933" : "#cc3333",
            color: "white",
            fontWeight: "bold",
          }}
        >
          {autoRefresh ? "自動更新中" : "更新停止中"}
        </button>
      </div>

      {/* Search conditions toggle */}
      <div style={{ marginBottom: "4px" }}>
        <button
          onClick={() => setShowSearchConditions(!showSearchConditions)}
          style={{
            ...btnStyle,
            fontSize: "11px",
            padding: "2px 8px",
          }}
        >
          検索条件 {showSearchConditions ? "▲" : "▼"}
        </button>
      </div>

      {/* Search conditions panel */}
      {showSearchConditions && (
        <div
          style={{
            backgroundColor: "#e8e8e8",
            padding: "6px",
            border: "1px solid #ccc",
            marginBottom: "4px",
            display: "grid",
            gridTemplateColumns: "auto 1fr auto 1fr auto 1fr",
            gap: "4px 8px",
            alignItems: "center",
          }}
        >
          <label style={{ fontWeight: "bold", whiteSpace: "nowrap" }}>
            伝票No
          </label>
          <input
            type="text"
            value={slipNo}
            onChange={(e) => {
              setSlipNo(e.target.value);
              handleSearchConditionChange();
            }}
            style={inputStyle}
            placeholder="前方一致"
          />
          <label style={{ fontWeight: "bold", whiteSpace: "nowrap" }}>
            Fromタンク
          </label>
          <input
            type="text"
            value={fromTank}
            onChange={(e) => {
              setFromTank(e.target.value);
              handleSearchConditionChange();
            }}
            style={inputStyle}
            placeholder="完全一致"
          />
          <label style={{ fontWeight: "bold", whiteSpace: "nowrap" }}>
            Toタンク
          </label>
          <input
            type="text"
            value={toTank}
            onChange={(e) => {
              setToTank(e.target.value);
              handleSearchConditionChange();
            }}
            style={inputStyle}
            placeholder="完全一致"
          />
          <label style={{ fontWeight: "bold", whiteSpace: "nowrap" }}>
            管理品名コード
          </label>
          <input
            type="text"
            value={itemCode}
            onChange={(e) => {
              setItemCode(e.target.value);
              handleSearchConditionChange();
            }}
            style={inputStyle}
            placeholder="前方一致"
          />
          <label style={{ fontWeight: "bold", whiteSpace: "nowrap" }}>
            管理品名
          </label>
          <input
            type="text"
            value={itemName}
            onChange={(e) => {
              setItemName(e.target.value);
              handleSearchConditionChange();
            }}
            style={inputStyle}
            placeholder="部分一致"
          />
        </div>
      )}

      {/* Order list info */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "2px",
        }}
      >
        <span style={{ fontWeight: "bold" }}>
          オーダ一覧（{orders.length}件）
        </span>
        <span style={{ color: "#666" }}>
          一覧表示日時: {searchedAt}
        </span>
      </div>

      {/* Order list table */}
      <div
        style={{
          overflowX: "auto",
          overflowY: "auto",
          maxHeight: "calc(100vh - 320px)",
          border: "1px solid #999",
          backgroundColor: "white",
        }}
      >
        <table
          style={{
            borderCollapse: "collapse",
            width: "100%",
            fontSize: "11px",
            minWidth: "1100px",
          }}
        >
          <thead>
            <tr style={{ backgroundColor: "#ddd", position: "sticky", top: 0 }}>
              <th style={thStyle}>STS</th>
              <th style={thStyle}>Fromタンク</th>
              <th style={thStyle}>Toタンク</th>
              <th style={{ ...thStyle, minWidth: "80px" }}>管理品名</th>
              <th style={thStyle}>計画量Net</th>
              <th style={thStyle} colSpan={2}>
                実績量
              </th>
              <th style={thStyle}>単位</th>
              <th style={thStyle}>伝票No</th>
              <th style={thStyle}>開始日時</th>
              <th style={thStyle}>終了日時</th>
            </tr>
            <tr style={{ backgroundColor: "#ddd", position: "sticky", top: "24px" }}>
              <th style={thStyle}></th>
              <th style={thStyle}></th>
              <th style={thStyle}></th>
              <th style={thStyle}></th>
              <th style={thStyle}></th>
              <th style={thStyle}>Net</th>
              <th style={thStyle}>Gross</th>
              <th style={thStyle}></th>
              <th style={thStyle}></th>
              <th style={thStyle}></th>
              <th style={thStyle}></th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={11} style={{ textAlign: "center", padding: "20px" }}>
                  読み込み中...
                </td>
              </tr>
            )}
            {!loading && orders.length === 0 && (
              <tr>
                <td colSpan={11} style={{ textAlign: "center", padding: "20px", color: "#999" }}>
                  データがありません
                </td>
              </tr>
            )}
            {!loading &&
              orders.map((order) => {
                const key = `${order.internal_no}-${order.slip_branch_no}`;
                const isSelected = selectedOrderKey === key;
                const bgColor = isSelected
                  ? "#cc99ff"
                  : getRowBgColor(order.shipping_status);

                return (
                  <tr
                    key={key}
                    onClick={() => handleOrderClick(order)}
                    onDoubleClick={() => handleOrderDoubleClick(order)}
                    style={{
                      backgroundColor: bgColor,
                      cursor: "pointer",
                    }}
                    onMouseEnter={(e) => {
                      if (!isSelected) {
                        (e.currentTarget as HTMLElement).style.backgroundColor =
                          "#e0e0ff";
                      }
                    }}
                    onMouseLeave={(e) => {
                      (e.currentTarget as HTMLElement).style.backgroundColor =
                        bgColor;
                    }}
                  >
                    <td style={tdStyle}>
                      {order.status_abbreviation || ""}
                    </td>
                    <td style={tdStyle}>{order.from_tank_no || ""}</td>
                    <td style={tdStyle}>{order.to_tank_no || ""}</td>
                    <td style={tdStyle} title={`${order.item_code || ""} ${order.item_name || ""}`}>
                      <div style={{ fontSize: "10px", color: "#666" }}>
                        {order.item_code || ""}
                      </div>
                      <div
                        style={{
                          maxWidth: "150px",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {order.item_name || ""}
                      </div>
                    </td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>
                      {formatNumber3(order.plan_quantity_net)}
                    </td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>
                      {formatNumber3(order.actual_net)}
                    </td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>
                      {formatNumber3(order.actual_gross)}
                    </td>
                    <td style={tdStyle}>kL</td>
                    <td style={tdStyle}>
                      {order.slip_no
                        ? `${order.slip_no}-${order.slip_branch_no}`
                        : ""}
                    </td>
                    <td style={tdStyle}>
                      {formatDatetime(order.transfer_start_datetime)}
                    </td>
                    <td style={tdStyle}>
                      {formatDatetime(order.transfer_end_datetime)}
                    </td>
                  </tr>
                );
              })}
          </tbody>
        </table>
      </div>

      {/* Batch selection area */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          marginTop: "8px",
          backgroundColor: "#e8e8e8",
          padding: "6px",
          border: "1px solid #ccc",
        }}
      >
        <span style={{ fontWeight: "bold" }}>バッチ選択</span>
        <select
          value={selectedBatchNo}
          onChange={(e) => setSelectedBatchNo(e.target.value)}
          disabled={!selectedOrder || batchList.length === 0}
          style={{
            padding: "2px 4px",
            fontSize: "12px",
            minWidth: "250px",
          }}
        >
          <option value="">-- 選択してください --</option>
          {batchList.map((b) => (
            <option key={b.batch_no} value={b.batch_no}>
              {b.batch_no} {b.batch_name}
            </option>
          ))}
        </select>

        {getRegisterButtonLabel() === "登録" && (
          <button
            onClick={handleRegister}
            disabled={isRegisterDisabled()}
            style={{
              ...btnStylePrimary,
              opacity: isRegisterDisabled() ? 0.5 : 1,
              cursor: isRegisterDisabled() ? "not-allowed" : "pointer",
            }}
          >
            登録
          </button>
        )}
        {getRegisterButtonLabel() === "設定/状況" && (
          <button onClick={handleBatchSetting} style={btnStyle}>
            設定/状況
          </button>
        )}
      </div>
    </div>
  );
}

const btnStyle: React.CSSProperties = {
  padding: "3px 10px",
  fontSize: "12px",
  backgroundColor: "#e0e0e0",
  border: "1px solid #999",
  cursor: "pointer",
  borderRadius: "2px",
};

const btnStylePrimary: React.CSSProperties = {
  ...btnStyle,
  backgroundColor: "#4488cc",
  color: "white",
  fontWeight: "bold",
};

const inputStyle: React.CSSProperties = {
  padding: "2px 4px",
  fontSize: "12px",
  border: "1px solid #999",
  width: "100%",
  boxSizing: "border-box",
};

const thStyle: React.CSSProperties = {
  border: "1px solid #999",
  padding: "3px 6px",
  textAlign: "center",
  whiteSpace: "nowrap",
  fontSize: "11px",
  fontWeight: "bold",
};

const tdStyle: React.CSSProperties = {
  border: "1px solid #ccc",
  padding: "2px 6px",
  whiteSpace: "nowrap",
  fontSize: "11px",
};
