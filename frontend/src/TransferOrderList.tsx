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
  // 移送中: 5, 15, 20, 26, 40 -> soft rose
  if ([5, 15, 20, 26, 40].includes(status)) return "#fef2f2";
  // バッチ割当: 1 -> soft amber
  if (status === 1) return "#fefce8";
  // 予約: 0 -> white
  if (status === 0) return "#ffffff";
  // 完了: 41 -> soft green
  if (status === 41) return "#f0fdf4";
  return "#ffffff";
}

/** Status badge color */
function getStatusBadgeStyle(status: number): React.CSSProperties {
  if ([5, 15, 20, 26, 40].includes(status))
    return { backgroundColor: "#fecaca", color: "#991b1b", border: "1px solid #fca5a5" };
  if (status === 1)
    return { backgroundColor: "#fef08a", color: "#854d0e", border: "1px solid #fde047" };
  if (status === 0)
    return { backgroundColor: "#e0e7ff", color: "#3730a3", border: "1px solid #c7d2fe" };
  if (status === 41)
    return { backgroundColor: "#bbf7d0", color: "#166534", border: "1px solid #86efac" };
  return { backgroundColor: "#f3f4f6", color: "#374151", border: "1px solid #d1d5db" };
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
    <div style={styles.pageWrapper}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerLeft}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 10 }}>
            <rect x="1" y="3" width="15" height="13" rx="2" /><polygon points="16 8 20 8 23 11 23 16 16 16 16 8" /><circle cx="5.5" cy="18.5" r="2.5" /><circle cx="18.5" cy="18.5" r="2.5" />
          </svg>
          <span style={styles.headerTitle}>移送オーダ一覧画面</span>
        </div>
        <div style={styles.headerRight}>
          <button
            onClick={handleAutoRefreshToggle}
            style={{
              ...styles.autoRefreshBtn,
              backgroundColor: autoRefresh ? "#dcfce7" : "#fee2e2",
              color: autoRefresh ? "#166534" : "#991b1b",
              borderColor: autoRefresh ? "#86efac" : "#fca5a5",
            }}
          >
            <span style={{
              display: "inline-block",
              width: 8,
              height: 8,
              borderRadius: "50%",
              backgroundColor: autoRefresh ? "#22c55e" : "#ef4444",
              marginRight: 6,
            }} />
            {autoRefresh ? "自動更新中" : "更新停止中"}
          </button>
        </div>
      </header>

      {/* Error message */}
      {errorMsg && (
        <div style={styles.errorBar}>
          <div style={styles.errorContent}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#dc2626" strokeWidth="2" style={{ flexShrink: 0 }}>
              <circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" />
            </svg>
            <span style={{ flex: 1 }}>{errorMsg}</span>
            <button onClick={() => setErrorMsg(null)} style={styles.errorCloseBtn}>
              OK
            </button>
          </div>
        </div>
      )}

      {/* Date & Action Bar */}
      <div style={styles.card}>
        <div style={styles.toolbarRow}>
          {/* Date section */}
          <div style={styles.dateSection}>
            <span style={styles.label}>移送日</span>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => {
                setDateFrom(e.target.value);
                handleSearchConditionChange();
              }}
              style={styles.dateInput}
            />
            <span style={{ color: "#9ca3af", fontSize: 13 }}>～</span>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => {
                setDateTo(e.target.value);
                handleSearchConditionChange();
              }}
              style={styles.dateInput}
            />
            <div style={styles.dateNavGroup}>
              <button onClick={handlePrevDay} style={styles.dateNavBtn}>＜前日</button>
              <button onClick={handleToday} style={styles.dateNavBtnActive}>今日</button>
              <button onClick={handleNextDay} style={styles.dateNavBtn}>翌日＞</button>
            </div>
          </div>

          {/* Action buttons */}
          <div style={styles.actionGroup}>
            <button onClick={handleDisplay} style={styles.btnPrimary}>
              表示
            </button>
            <button onClick={handleClear} style={styles.btnSecondary}>クリア</button>
            <button onClick={handleFileExport} style={styles.btnSecondary}>
              ファイル出力
            </button>
            <button onClick={handleOrderReceive} style={styles.btnSecondary}>オーダ受信</button>
          </div>
        </div>
      </div>

      {/* Search conditions toggle + panel */}
      <div style={styles.card}>
        <button
          onClick={() => setShowSearchConditions(!showSearchConditions)}
          style={styles.filterToggleBtn}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: 6 }}>
            <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
          </svg>
          検索条件
          <svg
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            style={{
              marginLeft: 6,
              transform: showSearchConditions ? "rotate(180deg)" : "rotate(0deg)",
              transition: "transform 0.2s ease",
            }}
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>

        {/* Search conditions panel */}
        {showSearchConditions && (
          <div style={styles.filterPanel}>
            <div style={styles.filterGrid}>
              <label style={styles.filterLabel}>伝票No</label>
              <input
                type="text"
                value={slipNo}
                onChange={(e) => {
                  setSlipNo(e.target.value);
                  handleSearchConditionChange();
                }}
                style={styles.filterInput}
                placeholder="前方一致"
              />
              <label style={styles.filterLabel}>Fromタンク</label>
              <input
                type="text"
                value={fromTank}
                onChange={(e) => {
                  setFromTank(e.target.value);
                  handleSearchConditionChange();
                }}
                style={styles.filterInput}
                placeholder="完全一致"
              />
              <label style={styles.filterLabel}>Toタンク</label>
              <input
                type="text"
                value={toTank}
                onChange={(e) => {
                  setToTank(e.target.value);
                  handleSearchConditionChange();
                }}
                style={styles.filterInput}
                placeholder="完全一致"
              />
              <label style={styles.filterLabel}>管理品名コード</label>
              <input
                type="text"
                value={itemCode}
                onChange={(e) => {
                  setItemCode(e.target.value);
                  handleSearchConditionChange();
                }}
                style={styles.filterInput}
                placeholder="前方一致"
              />
              <label style={styles.filterLabel}>管理品名</label>
              <input
                type="text"
                value={itemName}
                onChange={(e) => {
                  setItemName(e.target.value);
                  handleSearchConditionChange();
                }}
                style={styles.filterInput}
                placeholder="部分一致"
              />
            </div>
          </div>
        )}
      </div>

      {/* Order list section */}
      <div style={styles.card}>
        {/* List header */}
        <div style={styles.listHeader}>
          <div style={styles.listHeaderLeft}>
            <span style={styles.listTitle}>オーダ一覧</span>
            <span style={styles.listCount}>{orders.length}件</span>
          </div>
          <span style={styles.listTimestamp}>
            一覧表示日時: {searchedAt}
          </span>
        </div>

        {/* Order list table */}
        <div style={styles.tableWrapper}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>STS</th>
                <th style={styles.th}>Fromタンク</th>
                <th style={styles.th}>Toタンク</th>
                <th style={{ ...styles.th, minWidth: 100 }}>管理品名</th>
                <th style={{ ...styles.th, textAlign: "right" }}>計画量Net</th>
                <th style={{ ...styles.th, textAlign: "right" }} colSpan={2}>
                  実績量
                </th>
                <th style={styles.th}>単位</th>
                <th style={styles.th}>伝票No</th>
                <th style={styles.th}>開始日時</th>
                <th style={styles.th}>終了日時</th>
              </tr>
              <tr>
                <th style={styles.thSub}></th>
                <th style={styles.thSub}></th>
                <th style={styles.thSub}></th>
                <th style={styles.thSub}></th>
                <th style={styles.thSub}></th>
                <th style={styles.thSub}>Net</th>
                <th style={styles.thSub}>Gross</th>
                <th style={styles.thSub}></th>
                <th style={styles.thSub}></th>
                <th style={styles.thSub}></th>
                <th style={styles.thSub}></th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={11} style={{ textAlign: "center", padding: "40px 20px", color: "#94a3b8", fontSize: 13 }}>
                    読み込み中...
                  </td>
                </tr>
              )}
              {!loading && orders.length === 0 && (
                <tr>
                  <td colSpan={11} style={{ textAlign: "center", padding: "40px 20px", color: "#94a3b8", fontSize: 13 }}>
                    データがありません
                  </td>
                </tr>
              )}
              {!loading &&
                orders.map((order) => {
                  const key = `${order.internal_no}-${order.slip_branch_no}`;
                  const isSelected = selectedOrderKey === key;
                  const bgColor = isSelected
                    ? "#ede9fe"
                    : getRowBgColor(order.shipping_status);

                  return (
                    <tr
                      key={key}
                      onClick={() => handleOrderClick(order)}
                      onDoubleClick={() => handleOrderDoubleClick(order)}
                      style={{
                        backgroundColor: bgColor,
                        cursor: "pointer",
                        borderLeft: isSelected ? "3px solid #7c3aed" : "3px solid transparent",
                        transition: "background-color 0.15s ease",
                      }}
                      onMouseEnter={(e) => {
                        if (!isSelected) {
                          (e.currentTarget as HTMLElement).style.backgroundColor =
                            "#f5f3ff";
                        }
                      }}
                      onMouseLeave={(e) => {
                        (e.currentTarget as HTMLElement).style.backgroundColor =
                          bgColor;
                      }}
                    >
                      <td style={styles.td}>
                        <span style={{
                          ...styles.statusBadge,
                          ...getStatusBadgeStyle(order.shipping_status),
                        }}>
                          {order.status_abbreviation || ""}
                        </span>
                      </td>
                      <td style={styles.td}>{order.from_tank_no || ""}</td>
                      <td style={styles.td}>{order.to_tank_no || ""}</td>
                      <td style={styles.td} title={`${order.item_code || ""} ${order.item_name || ""}`}>
                        <div style={{ fontSize: 10, color: "#9ca3af", lineHeight: 1.2 }}>
                          {order.item_code || ""}
                        </div>
                        <div
                          style={{
                            maxWidth: 180,
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                            fontWeight: 500,
                          }}
                        >
                          {order.item_name || ""}
                        </div>
                      </td>
                      <td style={{ ...styles.td, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                        {formatNumber3(order.plan_quantity_net)}
                      </td>
                      <td style={{ ...styles.td, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                        {formatNumber3(order.actual_net)}
                      </td>
                      <td style={{ ...styles.td, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                        {formatNumber3(order.actual_gross)}
                      </td>
                      <td style={{ ...styles.td, textAlign: "center", color: "#6b7280" }}>kL</td>
                      <td style={styles.td}>
                        {order.slip_no
                          ? `${order.slip_no}-${order.slip_branch_no}`
                          : ""}
                      </td>
                      <td style={{ ...styles.td, color: "#6b7280", fontSize: 11 }}>
                        {formatDatetime(order.transfer_start_datetime)}
                      </td>
                      <td style={{ ...styles.td, color: "#6b7280", fontSize: 11 }}>
                        {formatDatetime(order.transfer_end_datetime)}
                      </td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Batch selection area */}
      <div style={styles.card}>
        <div style={styles.batchRow}>
          <span style={styles.batchLabel}>バッチ選択</span>
          <select
            value={selectedBatchNo}
            onChange={(e) => setSelectedBatchNo(e.target.value)}
            disabled={!selectedOrder || batchList.length === 0}
            style={{
              ...styles.batchSelect,
              opacity: (!selectedOrder || batchList.length === 0) ? 0.5 : 1,
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
                ...styles.btnPrimary,
                opacity: isRegisterDisabled() ? 0.4 : 1,
                cursor: isRegisterDisabled() ? "not-allowed" : "pointer",
              }}
            >
              登録
            </button>
          )}
          {getRegisterButtonLabel() === "設定/状況" && (
            <button onClick={handleBatchSetting} style={styles.btnSecondary}>
              設定/状況
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================
// Styles
// ============================================================

const styles: Record<string, React.CSSProperties> = {
  // Page
  pageWrapper: {
    fontFamily: "'Inter', 'Noto Sans JP', 'Meiryo', sans-serif",
    fontSize: 13,
    backgroundColor: "#f8fafc",
    minHeight: "100vh",
    padding: "0 20px 20px 20px",
  },

  // Header
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "14px 0",
    marginBottom: 12,
    borderBottom: "1px solid #e2e8f0",
  },
  headerLeft: {
    display: "flex",
    alignItems: "center",
    color: "#1e40af",
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: 700,
    color: "#1e293b",
    letterSpacing: "0.02em",
  },
  headerRight: {
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  autoRefreshBtn: {
    display: "inline-flex",
    alignItems: "center",
    padding: "6px 14px",
    fontSize: 12,
    fontWeight: 600,
    borderRadius: 20,
    border: "1px solid",
    cursor: "pointer",
    transition: "all 0.2s ease",
    backgroundColor: "transparent",
  },

  // Error
  errorBar: {
    backgroundColor: "#fef2f2",
    border: "1px solid #fecaca",
    borderRadius: 8,
    padding: "10px 16px",
    marginBottom: 12,
  },
  errorContent: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    color: "#dc2626",
    fontSize: 13,
  },
  errorCloseBtn: {
    padding: "4px 12px",
    fontSize: 12,
    backgroundColor: "#dc2626",
    color: "white",
    border: "none",
    borderRadius: 4,
    cursor: "pointer",
    fontWeight: 600,
  },

  // Card
  card: {
    backgroundColor: "#ffffff",
    borderRadius: 10,
    border: "1px solid #e2e8f0",
    padding: "14px 18px",
    marginBottom: 12,
    boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
  },

  // Toolbar
  toolbarRow: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
    flexWrap: "wrap" as const,
  },
  dateSection: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    flexWrap: "wrap" as const,
  },
  label: {
    fontSize: 12,
    fontWeight: 600,
    color: "#475569",
    marginRight: 2,
  },
  dateInput: {
    padding: "6px 10px",
    fontSize: 13,
    border: "1px solid #d1d5db",
    borderRadius: 6,
    color: "#1e293b",
    outline: "none",
    backgroundColor: "#f9fafb",
  },
  dateNavGroup: {
    display: "flex",
    borderRadius: 6,
    overflow: "hidden",
    border: "1px solid #d1d5db",
  },
  dateNavBtn: {
    padding: "6px 12px",
    fontSize: 12,
    backgroundColor: "#ffffff",
    border: "none",
    borderRight: "1px solid #e5e7eb",
    cursor: "pointer",
    color: "#374151",
    fontWeight: 500,
    transition: "background-color 0.15s ease",
  },
  dateNavBtnActive: {
    padding: "6px 12px",
    fontSize: 12,
    backgroundColor: "#eff6ff",
    border: "none",
    borderRight: "1px solid #e5e7eb",
    cursor: "pointer",
    color: "#2563eb",
    fontWeight: 600,
    transition: "background-color 0.15s ease",
  },
  actionGroup: {
    display: "flex",
    alignItems: "center",
    gap: 8,
  },

  // Buttons
  btnPrimary: {
    display: "inline-flex",
    alignItems: "center",
    padding: "7px 16px",
    fontSize: 13,
    fontWeight: 600,
    backgroundColor: "#2563eb",
    color: "#ffffff",
    border: "none",
    borderRadius: 6,
    cursor: "pointer",
    transition: "background-color 0.15s ease",
  },
  btnSecondary: {
    display: "inline-flex",
    alignItems: "center",
    padding: "7px 14px",
    fontSize: 13,
    fontWeight: 500,
    backgroundColor: "#ffffff",
    color: "#374151",
    border: "1px solid #d1d5db",
    borderRadius: 6,
    cursor: "pointer",
    transition: "all 0.15s ease",
  },

  // Filter toggle
  filterToggleBtn: {
    display: "inline-flex",
    alignItems: "center",
    padding: "6px 14px",
    fontSize: 13,
    fontWeight: 500,
    backgroundColor: "transparent",
    color: "#475569",
    border: "1px solid #e2e8f0",
    borderRadius: 6,
    cursor: "pointer",
    transition: "all 0.15s ease",
  },
  filterPanel: {
    marginTop: 12,
    paddingTop: 12,
    borderTop: "1px solid #f1f5f9",
  },
  filterGrid: {
    display: "grid",
    gridTemplateColumns: "auto 1fr auto 1fr auto 1fr",
    gap: "8px 12px",
    alignItems: "center",
  },
  filterLabel: {
    fontSize: 12,
    fontWeight: 600,
    color: "#64748b",
    whiteSpace: "nowrap",
  },
  filterInput: {
    padding: "7px 10px",
    fontSize: 13,
    border: "1px solid #d1d5db",
    borderRadius: 6,
    width: "100%",
    boxSizing: "border-box" as const,
    outline: "none",
    color: "#1e293b",
    backgroundColor: "#f9fafb",
    transition: "border-color 0.15s ease",
  },

  // List header
  listHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 10,
  },
  listHeaderLeft: {
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  listTitle: {
    fontSize: 14,
    fontWeight: 700,
    color: "#1e293b",
  },
  listCount: {
    fontSize: 12,
    fontWeight: 600,
    color: "#2563eb",
    backgroundColor: "#eff6ff",
    padding: "2px 10px",
    borderRadius: 12,
  },
  listTimestamp: {
    fontSize: 11,
    color: "#94a3b8",
  },

  // Table
  tableWrapper: {
    overflowX: "auto" as const,
    overflowY: "auto" as const,
    maxHeight: "calc(100vh - 380px)",
    borderRadius: 8,
    border: "1px solid #e2e8f0",
  },
  table: {
    borderCollapse: "collapse" as const,
    width: "100%",
    fontSize: 12,
    minWidth: 1100,
  },
  th: {
    backgroundColor: "#f8fafc",
    borderBottom: "2px solid #e2e8f0",
    padding: "10px 12px",
    textAlign: "left" as const,
    whiteSpace: "nowrap" as const,
    fontSize: 11,
    fontWeight: 600,
    color: "#64748b",
    textTransform: "uppercase" as const,
    letterSpacing: "0.04em",
    position: "sticky" as const,
    top: 0,
    zIndex: 1,
  },
  thSub: {
    backgroundColor: "#f8fafc",
    borderBottom: "1px solid #e2e8f0",
    padding: "4px 12px",
    textAlign: "center" as const,
    whiteSpace: "nowrap" as const,
    fontSize: 10,
    fontWeight: 600,
    color: "#94a3b8",
    position: "sticky" as const,
    top: 36,
    zIndex: 1,
  },
  td: {
    borderBottom: "1px solid #f1f5f9",
    padding: "8px 12px",
    whiteSpace: "nowrap" as const,
    fontSize: 12,
    color: "#334155",
  },
  statusBadge: {
    display: "inline-block",
    padding: "2px 8px",
    borderRadius: 4,
    fontSize: 11,
    fontWeight: 600,
    whiteSpace: "nowrap" as const,
    lineHeight: "18px",
  },

  // Batch
  batchRow: {
    display: "flex",
    alignItems: "center",
    gap: 12,
  },
  batchLabel: {
    fontSize: 13,
    fontWeight: 600,
    color: "#475569",
    whiteSpace: "nowrap" as const,
  },
  batchSelect: {
    padding: "7px 10px",
    fontSize: 13,
    border: "1px solid #d1d5db",
    borderRadius: 6,
    minWidth: 280,
    color: "#1e293b",
    backgroundColor: "#f9fafb",
    outline: "none",
  },
};
