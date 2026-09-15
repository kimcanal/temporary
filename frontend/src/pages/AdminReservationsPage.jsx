import { useEffect, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";

const STATUS_LABELS = {
  confirmed: "확정",
  checked_in: "체크인",
  cancelled: "취소",
  no_show: "노쇼",
  completed: "완료",
};

const CANCELLABLE_STATUSES = ["confirmed", "checked_in"];

function todayKST() {
  const fmt = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Seoul" });
  return fmt.format(new Date());
}

function formatTime(iso) {
  return new Date(iso).toLocaleTimeString("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Seoul",
  });
}

function partyLabel(row) {
  if (row.is_admin_block) return `🔒 관리자 차단${row.note ? ` · ${row.note}` : ""}`;
  const name = row.user_name || `사용자 #${row.user_id}`;
  return row.party_size > 1 ? `${name} 외 ${row.party_size - 1}명` : name;
}

function statusLabel(row) {
  if (row.is_admin_block) return row.status === "cancelled" ? "차단 해제됨" : "차단";
  return STATUS_LABELS[row.status] || row.status;
}

export default function AdminReservationsPage() {
  const { token } = useAuth();
  const [date, setDate] = useState(todayKST());
  const [spaces, setSpaces] = useState([]);
  const [spaceId, setSpaceId] = useState("");
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");

  useEffect(() => {
    api
      .spaces(token)
      .then(setSpaces)
      .catch(() => {});
  }, [token]);

  function load() {
    setLoading(true);
    setError("");
    api
      .adminReservations(date, spaceId || null, token)
      .then(setRows)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(load, [date, spaceId, token]);

  async function cancel(id) {
    setError("");
    setMsg("");
    try {
      await api.cancel(id, token);
      setMsg(`예약 #${id}을(를) 취소했습니다.`);
      load();
    } catch (e) {
      setError(e.message);
    }
  }

  const activeRows = rows.filter((r) => CANCELLABLE_STATUSES.includes(r.status));
  const totalPeople = activeRows
    .filter((r) => !r.is_admin_block)
    .reduce((sum, r) => sum + r.party_size, 0);
  const blockedCount = activeRows.filter((r) => r.is_admin_block).length;

  return (
    <div>
      <div className="hero">
        <span className="eyebrow">관리자</span>
        <h1>예약 현황</h1>
        <p className="muted" style={{ margin: 0 }}>
          날짜별로 어떤 공간을 누가, 몇 명이 쓰는지 확인하고 필요하면 예약을 취소할 수 있습니다.
        </p>
      </div>

      <div className="toolbar">
        <label style={{ minWidth: 160 }}>
          날짜 (KST)
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </label>
        <label style={{ minWidth: 180 }}>
          공간
          <select value={spaceId} onChange={(e) => setSpaceId(e.target.value)}>
            <option value="">전체</option>
            {spaces.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        <button type="button" className="ghost" onClick={load}>
          새로고침
        </button>
      </div>

      {msg && <p className="ok">{msg}</p>}
      {error && <p className="err">{error}</p>}
      {!loading && rows.length > 0 && (
        <p className="muted" style={{ fontSize: "0.88rem" }}>
          이 날짜 활성 예약 {activeRows.length}건 · 총 이용 인원 {totalPeople}명
          {blockedCount > 0 && ` · 관리자 차단 ${blockedCount}건`}
        </p>
      )}

      <div style={{ display: "grid", gap: "0.75rem" }}>
        {loading && <p className="muted">불러오는 중…</p>}
        {!loading && rows.length === 0 && !error && (
          <p className="muted">이 날짜에 예약이 없습니다.</p>
        )}
        {rows.map((r) => (
          <div
            key={r.id}
            className="card"
            style={{ display: "flex", gap: "1rem", flexWrap: "wrap", alignItems: "center" }}
          >
            <div style={{ flex: 1, minWidth: 220 }}>
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" }}>
                <strong>#{r.id}</strong>
                <span>{r.space_name || `공간 ${r.space_id}`}</span>
                <span className={`status-pill ${r.status}`}>{statusLabel(r)}</span>
              </div>
              <div className="muted" style={{ marginTop: "0.35rem", fontSize: "0.92rem" }}>
                {formatTime(r.start_at)}–{formatTime(r.end_at)} · {partyLabel(r)}
              </div>
            </div>
            {CANCELLABLE_STATUSES.includes(r.status) && (
              <button className="danger" type="button" onClick={() => cancel(r.id)}>
                취소
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
