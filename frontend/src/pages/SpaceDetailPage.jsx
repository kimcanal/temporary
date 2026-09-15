import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";

// Fallback used only until the real daily limit loads from the server.
const DEFAULT_DAILY_LIMIT_HOURS = 2;

function todayKST() {
  const fmt = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
  return fmt.format(new Date());
}

function overlaps(aStart, aEnd, bStart, bEnd) {
  return aStart < bEnd && aEnd > bStart;
}

function slotClassName(slot, isSelected, isMine) {
  if (isSelected) return "slot slot-selected";
  if (isMine) return "slot slot-mine";
  if (slot.available) return "slot slot-available";
  return "slot slot-booked";
}

const KST_HOUR_FORMAT = new Intl.DateTimeFormat("en-US", {
  hour: "2-digit",
  hourCycle: "h23",
  timeZone: "Asia/Seoul",
});

function isAfternoon(iso) {
  return Number(KST_HOUR_FORMAT.format(new Date(iso))) >= 12;
}

function formatClock(iso) {
  return new Date(iso).toLocaleTimeString("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Seoul",
  });
}

export default function SpaceDetailPage() {
  const { id } = useParams();
  const { token, user } = useAuth();
  const isAdmin = !!user?.is_admin;
  const [space, setSpace] = useState(null);
  const [date, setDate] = useState(todayKST());
  const [slots, setSlots] = useState([]);
  const [mineStarts, setMineStarts] = useState(new Set());
  const [selected, setSelected] = useState([]);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [dailyLimitHours, setDailyLimitHours] = useState(DEFAULT_DAILY_LIMIT_HOURS);
  const [partySize, setPartySize] = useState(1);
  const [blockReason, setBlockReason] = useState("");
  const [blocking, setBlocking] = useState(false);

  useEffect(() => {
    api
      .settings(token)
      .then((s) => setDailyLimitHours(s.daily_limit_hours))
      .catch(() => {});
  }, [token]);

  function load() {
    setError("");
    Promise.all([api.space(id, token), api.slots(id, date, token), api.mine(token).catch(() => [])])
      .then(([sp, sl, mine]) => {
        setSpace(sp);
        setPartySize((prev) => Math.min(prev, sp.capacity));
        const list = sl.slots || [];
        setSlots(list);
        setSelected([]);
        const mineSet = new Set();
        const dayMine = (mine || []).filter(
          (r) =>
            String(r.space_id) === String(id) &&
            (r.status === "confirmed" || r.status === "checked_in")
        );
        for (const slot of list) {
          const s0 = new Date(slot.start_at).getTime();
          const s1 = new Date(slot.end_at).getTime();
          for (const r of dayMine) {
            const r0 = new Date(r.start_at).getTime();
            const r1 = new Date(r.end_at).getTime();
            if (overlaps(s0, s1, r0, r1)) {
              mineSet.add(slot.start_at);
              break;
            }
          }
        }
        setMineStarts(mineSet);
      })
      .catch((e) => setError(e.message));
  }

  useEffect(load, [id, date, token]);

  // `selected` is always a chronologically contiguous run of start_at values
  // (see toggle()), so the first/last entries are the range's edges.
  const selectedRange = useMemo(() => {
    if (!selected.length) return null;
    const first = slots.find((s) => s.start_at === selected[0]);
    const last = slots.find((s) => s.start_at === selected[selected.length - 1]);
    if (!first || !last) return null;
    return { start_at: first.start_at, end_at: last.end_at };
  }, [selected, slots]);

  const morningSlots = useMemo(() => slots.filter((s) => !isAfternoon(s.start_at)), [slots]);
  const afternoonSlots = useMemo(() => slots.filter((s) => isAfternoon(s.start_at)), [slots]);

  // Slot length in minutes, read from the actual data rather than assumed,
  // so this stays correct if an admin changes the slot size.
  const slotMinutes = slots.length
    ? (new Date(slots[0].end_at) - new Date(slots[0].start_at)) / 60000
    : 30;
  const maxSlotsPerBooking = Math.max(1, Math.floor((dailyLimitHours * 60) / slotMinutes));

  // Click one slot to start a selection, then click a later (or earlier) slot
  // to fill in everything between the two as one range — no need to click
  // every slot in between one at a time.
  function toggle(slot) {
    setMsg("");

    if (selected.includes(slot.start_at)) {
      setError("");
      const idx = selected.indexOf(slot.start_at);
      if (idx === 0) {
        setSelected(selected.slice(1));
      } else if (idx === selected.length - 1) {
        setSelected(selected.slice(0, -1));
      } else {
        setSelected([]);
      }
      return;
    }

    if (!slot.available) return;

    if (selected.length === 0) {
      setError("");
      setSelected([slot.start_at]);
      return;
    }

    const anchorIndex = slots.findIndex((s) => s.start_at === selected[0]);
    const targetIndex = slots.findIndex((s) => s.start_at === slot.start_at);
    const [lo, hi] = anchorIndex < targetIndex ? [anchorIndex, targetIndex] : [targetIndex, anchorIndex];
    const range = slots.slice(lo, hi + 1);

    if (range.some((s) => !s.available)) {
      setError("선택한 구간에 예약할 수 없는 슬롯이 포함되어 있습니다.");
      return;
    }
    // Admins can select a longer range to block off (e.g. a whole class), so the
    // per-user daily-hour cap only applies to a regular booking selection.
    if (!isAdmin && range.length > maxSlotsPerBooking) {
      setError(
        `하루 최대 ${dailyLimitHours}시간(${slotMinutes}분 × ${maxSlotsPerBooking}슬롯)까지 예약할 수 있습니다.`
      );
      return;
    }
    setError("");
    setSelected(range.map((s) => s.start_at));
  }

  function renderSlot(slot) {
    const label = new Date(slot.start_at).toLocaleTimeString("ko-KR", {
      hour: "2-digit",
      minute: "2-digit",
      timeZone: "Asia/Seoul",
    });
    const isSel = selected.includes(slot.start_at);
    const isMine = mineStarts.has(slot.start_at);

    return (
      <button
        key={slot.start_at}
        type="button"
        className={slotClassName(slot, isSel, isMine)}
        onClick={() => toggle(slot)}
        disabled={!slot.available && !isSel}
        title={isMine ? "내 예약" : slot.available ? "예약 가능" : "예약 불가"}
      >
        {label}
      </button>
    );
  }

  async function book() {
    if (!selectedRange) return;
    setBusy(true);
    setError("");
    setMsg("");
    try {
      const r = await api.book(
        {
          space_id: Number(id),
          start_at: selectedRange.start_at,
          end_at: selectedRange.end_at,
          party_size: partySize,
        },
        token
      );
      setMsg(`예약 완료 #${r.id} (${r.status})`);
      load();
    } catch (err) {
      setError(err.status === 409 ? `409 Conflict: ${err.message}` : err.message);
    } finally {
      setBusy(false);
    }
  }

  async function blockSelection() {
    if (!selectedRange) return;
    setBlocking(true);
    setError("");
    setMsg("");
    try {
      await api.createBlock(
        {
          space_id: Number(id),
          start_at: selectedRange.start_at,
          end_at: selectedRange.end_at,
          reason: blockReason || null,
        },
        token
      );
      setMsg("선택한 시간대를 차단했습니다.");
      setBlockReason("");
      load();
    } catch (err) {
      setError(err.status === 409 ? `409 Conflict: ${err.message}` : err.message);
    } finally {
      setBlocking(false);
    }
  }

  return (
    <div>
      <p style={{ marginBottom: "0.5rem" }}>
        <Link to="/">← 공간 목록</Link>
      </p>
      <div className="hero">
        <span className="eyebrow">슬롯 예약</span>
        <h1>{space?.name || "공간"}</h1>
        {space && (
          <p className="muted" style={{ margin: 0 }}>
            {space.location} · 정원 {space.capacity}명 · 운영{" "}
            {space.open_time?.slice(0, 5)}–{space.close_time?.slice(0, 5)}
          </p>
        )}
      </div>

      <div className="toolbar">
        <label style={{ minWidth: 160 }}>
          날짜 (KST)
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </label>
        <label style={{ minWidth: 110 }}>
          이용 인원
          <input
            type="number"
            min="1"
            max={space?.capacity || 1}
            value={partySize}
            onChange={(e) => setPartySize(Number(e.target.value) || 1)}
          />
        </label>
        <button type="button" className="ghost" onClick={load}>
          새로고침
        </button>
        <button type="button" onClick={book} disabled={!selectedRange || busy}>
          {busy ? "예약 중…" : `선택 예약 (${selected.length * slotMinutes}분)`}
        </button>
      </div>
      <p style={{ fontSize: "0.95rem", fontWeight: 600, margin: "-0.4rem 0 0.5rem" }}>
        {selectedRange
          ? `선택한 시간: ${formatClock(selectedRange.start_at)} ~ ${formatClock(selectedRange.end_at)} (${
              selected.length * slotMinutes
            }분)`
          : "선택한 시간: 아래 슬롯에서 시작과 끝을 클릭하세요."}
      </p>
      {space && (
        <p className="muted" style={{ fontSize: "0.85rem", margin: "0 0 1rem" }}>
          이 공간 정원은 {space.capacity}명입니다.
        </p>
      )}

      {isAdmin && (
        <div className="toolbar" style={{ marginTop: "-0.5rem" }}>
          <label style={{ minWidth: 220, flex: 1 }}>
            차단 사유 (예: 학교 수업)
            <input
              type="text"
              value={blockReason}
              onChange={(e) => setBlockReason(e.target.value)}
              placeholder="선택 사항"
            />
          </label>
          <button
            type="button"
            className="ghost"
            onClick={blockSelection}
            disabled={!selectedRange || blocking}
          >
            {blocking ? "차단 중…" : "선택 구간 차단"}
          </button>
        </div>
      )}

      {msg && <p className="ok">{msg}</p>}
      {error && <p className="err">{error}</p>}

      <div className="slot-legend">
        <span>
          <i style={{ background: "#fff", borderColor: "#d4c9bb" }} />
          예약 가능
        </span>
        <span>
          <i style={{ background: "#9b2335" }} />
          선택됨
        </span>
        <span>
          <i style={{ background: "#f5edd8", borderColor: "#c4a35a" }} />
          내 예약
        </span>
        <span>
          <i style={{ background: "#efe8df" }} />
          예약됨/지난 시간
        </span>
      </div>
      <p className="muted" style={{ fontSize: "0.85rem", margin: "-0.35rem 0 0.9rem" }}>
        시작 슬롯과 끝 슬롯을 순서대로 클릭하면 그 사이 시간이 자동으로 선택됩니다.
      </p>

      {morningSlots.length > 0 && (
        <div className="slot-section">
          <h2 className="slot-section-title">오전</h2>
          <div className="slot-grid">{morningSlots.map((slot) => renderSlot(slot))}</div>
        </div>
      )}
      {afternoonSlots.length > 0 && (
        <div className="slot-section">
          <h2 className="slot-section-title">오후</h2>
          <div className="slot-grid">{afternoonSlots.map((slot) => renderSlot(slot))}</div>
        </div>
      )}
      {slots.length === 0 && !error && <p className="muted">이 날짜에 표시할 슬롯이 없습니다.</p>}
    </div>
  );
}
