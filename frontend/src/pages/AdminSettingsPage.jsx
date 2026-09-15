import { useEffect, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";

const SLOT_MINUTE_OPTIONS = [30, 60];
const DAILY_LIMIT_HOUR_OPTIONS = [1, 2, 3, 4, 5, 6, 7, 8];

function slotLabel(minutes) {
  return minutes % 60 === 0 ? `${minutes / 60}시간` : `${minutes}분`;
}

// Keep the loaded value selectable even if it isn't one of the presets
// (e.g. it was set some other way before), instead of silently losing it.
function withCurrentValue(options, current) {
  const n = Number(current);
  return options.includes(n) ? options : [...options, n].sort((a, b) => a - b);
}

export default function AdminSettingsPage() {
  const { token } = useAuth();
  const [form, setForm] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .settings(token)
      .then(setForm)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token]);

  async function onSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    setMsg("");
    try {
      const saved = await api.updateSettings(
        {
          daily_limit_hours: Number(form.daily_limit_hours),
          slot_minutes: Number(form.slot_minutes),
          checkin_grace_minutes: Number(form.checkin_grace_minutes),
        },
        token
      );
      setForm(saved);
      setMsg("설정을 저장했습니다.");
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  const maxSlots =
    form && form.slot_minutes > 0 ? Math.floor((form.daily_limit_hours * 60) / form.slot_minutes) : null;
  const slotOptions = form ? withCurrentValue(SLOT_MINUTE_OPTIONS, form.slot_minutes) : SLOT_MINUTE_OPTIONS;
  const limitOptions = form
    ? withCurrentValue(DAILY_LIMIT_HOUR_OPTIONS, form.daily_limit_hours)
    : DAILY_LIMIT_HOUR_OPTIONS;

  return (
    <div>
      <div className="hero">
        <span className="eyebrow">관리자</span>
        <h1>예약 규칙 설정</h1>
        <p className="muted" style={{ margin: 0 }}>
          하루 예약 한도, 슬롯 단위, 체크인 유예 시간을 조정합니다. 저장하면 새로 만드는 예약부터 바로
          적용됩니다.
        </p>
      </div>

      {loading && <p className="muted">불러오는 중…</p>}
      {msg && <p className="ok">{msg}</p>}
      {error && <p className="err">{error}</p>}

      {form && (
        <form onSubmit={onSubmit} className="card" style={{ display: "grid", gap: "1.1rem", maxWidth: 480 }}>
          <label>
            하루 예약 한도
            <select
              value={form.daily_limit_hours}
              onChange={(e) => setForm({ ...form, daily_limit_hours: e.target.value })}
            >
              {limitOptions.map((h) => (
                <option key={h} value={h}>
                  {h}시간
                </option>
              ))}
            </select>
          </label>
          <label>
            슬롯 단위
            <select
              value={form.slot_minutes}
              onChange={(e) => setForm({ ...form, slot_minutes: e.target.value })}
            >
              {slotOptions.map((m) => (
                <option key={m} value={m}>
                  {slotLabel(m)}
                </option>
              ))}
            </select>
          </label>
          <label>
            체크인 유예 시간 (분)
            <input
              type="number"
              min="0"
              max="180"
              step="1"
              value={form.checkin_grace_minutes}
              onChange={(e) => setForm({ ...form, checkin_grace_minutes: e.target.value })}
              required
            />
          </label>

          {maxSlots !== null && (
            <p className="muted" style={{ margin: 0, fontSize: "0.88rem" }}>
              한 번에 최대 {maxSlots}슬롯({form.daily_limit_hours}시간)까지 연속 예약할 수 있습니다.
            </p>
          )}

          <button type="submit" disabled={saving}>
            {saving ? "저장 중…" : "저장"}
          </button>
        </form>
      )}
    </div>
  );
}
