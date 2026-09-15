import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function SpacesPage() {
  const { token } = useAuth();
  const [spaces, setSpaces] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .spaces(token)
      .then(setSpaces)
      .catch((e) => setError(e.message));
  }, [token]);

  return (
    <div>
      <div className="hero">
        <span className="eyebrow">서강대학교 · A+ 원정대</span>
        <h1>공간 목록</h1>
        <p className="muted" style={{ margin: 0, maxWidth: 560 }}>
          캠퍼스 스터디룸을 선택해 30분 단위 슬롯을 예약하세요. 같은 시간대 중복 예약은 DB에서 차단됩니다 (409).
        </p>
      </div>
      {error && <p className="err">{error}</p>}
      <div className="space-grid">
        {spaces.map((s) => (
          <Link key={s.id} to={`/spaces/${s.id}`} className="card card-hover space-card" style={{ color: "inherit" }}>
            <h3 style={{ margin: "0 0 0.4rem", fontSize: "1.2rem" }}>{s.name}</h3>
            <p className="muted" style={{ margin: 0, minHeight: "2.6em", fontSize: "0.92rem" }}>
              {s.description || "설명 없음"}
            </p>
            <div className="meta">
              <span className="chip">📍 {s.location || "위치 미정"}</span>
              <span className="chip gold">👥 {s.capacity}명</span>
              <span className="chip">
                🕒 {s.open_time?.slice(0, 5)}–{s.close_time?.slice(0, 5)}
              </span>
            </div>
          </Link>
        ))}
      </div>
      {spaces.length === 0 && !error && <p className="muted">등록된 공간이 없습니다.</p>}
    </div>
  );
}
