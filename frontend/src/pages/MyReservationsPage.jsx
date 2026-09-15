import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";

const STATUS_LABELS = {
  confirmed: "확정",
  checked_in: "체크인",
  cancelled: "취소",
  no_show: "노쇼",
  completed: "완료",
};

const CANCELLABLE_STATUSES = ["confirmed"];

function formatKST(iso) {
  return new Date(iso).toLocaleString("ko-KR", { timeZone: "Asia/Seoul" });
}

export default function MyReservationsPage() {
  const { token } = useAuth();
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");

  function load() {
    api
      .mine(token)
      .then(setRows)
      .catch((e) => setError(e.message));
  }

  useEffect(load, [token]);

  async function cancel(id) {
    setError("");
    try {
      await api.cancel(id, token);
      setMsg(`예약 #${id}을(를) 취소했습니다.`);
      load();
    } catch (e) {
      setError(e.message);
    }
  }

  async function checkIn(id) {
    setError("");
    try {
      await api.checkIn(id, token);
      setMsg(`예약 #${id} 체크인 완료`);
      load();
    } catch (e) {
      setError(e.message);
    }
  }

  async function checkOut(id) {
    setError("");
    try {
      await api.checkOut(id, token);
      setMsg(`예약 #${id} 조기 퇴실 처리했습니다. 남은 시간은 다른 사람이 예약할 수 있습니다.`);
      load();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div>
      <div className="hero">
        <span className="eyebrow">내 예약</span>
        <h1>내 예약</h1>
        <p className="muted" style={{ margin: 0 }}>
          예약을 확인하고 체크인하거나 취소할 수 있습니다.{" "}
          <Link to="/">공간 목록으로</Link>
        </p>
      </div>
      {msg && <p className="ok">{msg}</p>}
      {error && <p className="err">{error}</p>}
      <div style={{ display: "grid", gap: "0.75rem" }}>
        {rows.length === 0 && <p className="muted">아직 예약이 없습니다.</p>}
        {rows.map((r) => (
          <div
            key={r.id}
            className="card"
            style={{ display: "flex", gap: "1rem", flexWrap: "wrap", alignItems: "center" }}
          >
            <div style={{ flex: 1, minWidth: 200 }}>
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" }}>
                <strong>#{r.id}</strong>
                <span>{r.space_name || `공간 ${r.space_id}`}</span>
                <span className={`status-pill ${r.status}`}>{STATUS_LABELS[r.status] || r.status}</span>
              </div>
              <div className="muted" style={{ marginTop: "0.35rem", fontSize: "0.92rem" }}>
                {formatKST(r.start_at)} → {formatKST(r.end_at)} · 인원 {r.party_size}명
              </div>
            </div>
            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
              {CANCELLABLE_STATUSES.includes(r.status) && (
                <button className="danger" type="button" onClick={() => cancel(r.id)}>
                  취소
                </button>
              )}
              {r.status === "confirmed" && (
                <button className="success" type="button" onClick={() => checkIn(r.id)}>
                  체크인
                </button>
              )}
              {r.status === "checked_in" && (
                <button className="ghost" type="button" onClick={() => checkOut(r.id)}>
                  조기 퇴실
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
