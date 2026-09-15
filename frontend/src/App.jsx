import { Navigate, Route, Routes, Link } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import SpacesPage from "./pages/SpacesPage";
import SpaceDetailPage from "./pages/SpaceDetailPage";
import MyReservationsPage from "./pages/MyReservationsPage";
import AdminSettingsPage from "./pages/AdminSettingsPage";
import AdminReservationsPage from "./pages/AdminReservationsPage";

function Shell({ children }) {
  const { user, logout } = useAuth();
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="container app-header-inner">
          <Link to="/" className="brand">
            <div className="brand-mark" aria-hidden>
              서
            </div>
            <div className="brand-text">
              <strong>SlotLock</strong>
              <span>서강대학교 · 스터디룸 예약</span>
            </div>
          </Link>
          <span className="muted app-header-team" style={{ fontSize: "0.8rem" }}>
            A+ 원정대 · CSE4022
          </span>
          <nav className="app-nav">
            {user && (
              <>
                <Link to="/">공간 목록</Link>
                <Link to="/mine">내 예약</Link>
                {user.is_admin && <Link to="/admin/reservations">예약 현황</Link>}
                {user.is_admin && <Link to="/admin/settings">관리자 설정</Link>}
                <span className="muted app-header-username" style={{ fontSize: "0.88rem" }}>
                  {user.full_name}
                </span>
                <button className="ghost" type="button" onClick={logout}>
                  로그아웃
                </button>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className="container">{children}</main>
      <footer className="app-footer">
        <div className="container">
          <strong>SlotLock</strong> · 서강대학교 스터디룸 예약 · A+ 원정대 · CSE4022
        </div>
      </footer>
    </div>
  );
}

function Private({ children }) {
  const { token, loading } = useAuth();
  if (loading) return <p className="muted">불러오는 중…</p>;
  if (!token) return <Navigate to="/login" replace />;
  return children;
}

function AdminOnly({ children }) {
  const { user } = useAuth();
  if (!user?.is_admin) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  return (
    <Shell>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route
          path="/"
          element={
            <Private>
              <SpacesPage />
            </Private>
          }
        />
        <Route
          path="/spaces/:id"
          element={
            <Private>
              <SpaceDetailPage />
            </Private>
          }
        />
        <Route
          path="/mine"
          element={
            <Private>
              <MyReservationsPage />
            </Private>
          }
        />
        <Route
          path="/admin/settings"
          element={
            <Private>
              <AdminOnly>
                <AdminSettingsPage />
              </AdminOnly>
            </Private>
          }
        />
        <Route
          path="/admin/reservations"
          element={
            <Private>
              <AdminOnly>
                <AdminReservationsPage />
              </AdminOnly>
            </Private>
          }
        />
      </Routes>
    </Shell>
  );
}
