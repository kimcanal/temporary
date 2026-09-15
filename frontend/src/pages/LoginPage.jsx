import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const { login, token } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("student@slotlock.local");
  const [password, setPassword] = useState("student123");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (token) return <Navigate to="/" replace />;

  async function onSubmit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
      nav("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <div className="card">
        <div className="auth-badge">서강대학교 · SlotLock</div>
        <h1 style={{ marginTop: 0 }}>로그인</h1>
        <p className="muted" style={{ marginTop: 0 }}>
          스터디룸을 예약하려면 계정으로 로그인해 주세요.
        </p>
        <div className="demo-box">
          데모 학생 계정: <code>student@slotlock.local</code> / <code>student123</code>
          <br />
          데모 관리자 계정: <code>admin</code> / <code>admin</code>
        </div>
        <form onSubmit={onSubmit} style={{ display: "grid", gap: "0.9rem" }}>
          <label>
            아이디
            <input value={email} onChange={(e) => setEmail(e.target.value)} type="text" required autoComplete="username" />
          </label>
          <label>
            비밀번호
            <input
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type="password"
              required
              autoComplete="current-password"
            />
          </label>
          {error && <p className="err">{error}</p>}
          <button type="submit" disabled={busy}>
            {busy ? "로그인 중…" : "로그인"}
          </button>
        </form>
        <p className="muted" style={{ marginTop: "1.1rem", marginBottom: 0 }}>
          계정이 없으신가요? <Link to="/register">회원가입</Link>
        </p>
      </div>
    </div>
  );
}
