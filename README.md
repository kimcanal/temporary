# SlotLock — 서강대학교 스터디룸 예약 MVP

**Team:** A+ 원정대 · **Course:** CSE4022  
**Goal:** Prove that concurrent bookings cannot double-book the same space/time using PostgreSQL `EXCLUDE USING gist` (`btree_gist`).

한국어 요약: 스터디룸 예약 시스템 MVP입니다. 동일 공간의 시간 겹침은 DB exclusion constraint로 차단되며, 동시 요청 시 하나만 성공하고 나머지는 HTTP **409 Conflict**를 받습니다.

데모 공간 예시: 곤자가 플라자 스터디룸 A, 로욜라 도서관 그룹룸 3, 다산관 세미나실 B, 엠마오관 회의실 1.

---


## 학교 VDI에서 실행 (Ubuntu)

1. 채팅에서 받은 `SlotLock_MVP.tar.gz`를 VDI로 복사한다.
2. 터미널에서:

```bash
tar -xzf SlotLock_MVP.tar.gz
cd slotlock
docker compose up --build
# 구버전이면: docker-compose up --build
```

3. 브라우저:
   - 화면: http://localhost:3000
   - API 문서: http://localhost:8000/docs
4. 로그인: `student@slotlock.local` / `student123`
5. 데모: 같은 방·같은 시간에 두 번 예약해 보면 두 번째는 **409**로 막힌다.

VDI에 Docker가 없으면 관리자/실습 안내대로 Docker(또는 docker-compose)만 설치한 뒤 위 명령을 다시 실행하면 된다.

---
## Quick start

### Option A — Docker Compose (recommended)

```bash
cd /workspace/slotlock
docker compose config          # or: docker-compose config
docker compose up --build      # or: docker-compose up --build
```

> **Note (WSL2 dev machines):** All services have `restart: unless-stopped`, so they come back on
> their own if the Docker daemon bounces. If the WSL VM itself was shut down (e.g. it went idle),
> just `cd slotlock && docker compose up -d` again. To stop WSL from idling out on its own, add
> `vmIdleTimeout=-1` under `[wsl2]` in `%UserProfile%\.wslconfig` and `wsl --shutdown` once.

> **Note (sandbox / some VMs):** If containers cannot reach each other on the bridge network,
> ensure Docker uses `iptables-legacy` (`update-alternatives --set iptables /usr/sbin/iptables-legacy`)
> and restart `dockerd`. Standard Linux desktops usually work without this.

| Service | URL |
|---------|-----|
| Web UI  | http://localhost:3000 |
| API     | http://localhost:8000 |
| OpenAPI | http://localhost:8000/docs |
| Postgres| localhost:5432 (`slotlock` / `slotlock`) |
| Redis   | localhost:6379 |

Demo accounts (seeded on API startup):

| Email | Password | Role |
|-------|----------|------|
| `student@slotlock.local` | `student123` | student |
| `admin` | `admin` | admin |

Log in as admin and open **관리자 설정** in the nav (`/admin/settings`) to change the daily booking
limit, slot size, and check-in grace period at runtime — no redeploy needed.

### Option B — Local (Postgres + Redis already running)

```bash
# Backend
cd /workspace/slotlock/backend
python -m venv ../../slotlock-venv && source ../../slotlock-venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg2://slotlock:slotlock@localhost:5432/slotlock
export REDIS_URL=redis://localhost:6379/0
export PYTHONPATH=.
alembic upgrade head   # or rely on startup create_all + seed
python scripts/seed.py
uvicorn app.main:app --reload --port 8000

# Frontend (another terminal)
cd /workspace/slotlock/frontend
npm install && npm run dev
# → http://localhost:5173
```

Copy `.env.example` to `.env` and adjust as needed.

---

## Architecture

```
React (Vite) ──JWT──▶ FastAPI ──SQLAlchemy──▶ PostgreSQL 16
                         │                      └ EXCLUDE USING gist
                         └── Redis (slot cache, optional)
```

| Layer | Responsibility |
|-------|----------------|
| **Auth** | Register / login, JWT bearer (`/api/auth/*`) |
| **Spaces** | List / detail / admin create; slot grid by date |
| **Reservations** | Create / cancel / check-in / check-out (early release) / mine |
| **DB invariant** | `EXCLUDE USING gist (space_id WITH =, tstzrange(start_at,end_at,'[)') WITH &&) WHERE status IN ('confirmed','checked_in')` |
| **Business** | Operating hours, daily ≤ 2h limit, half-open ranges so adjacent slots OK |
| **Cache** | Redis TTL cache for `GET /spaces/{id}/slots` (disabled gracefully if Redis down) |

Module layout (`backend/app/`): `api/`, `core/`, `models/`, `schemas/`, `services/`, `scripts/`.

---

## How to demo the 409 conflict

1. Login as `student@slotlock.local`.
2. Open a space → pick tomorrow’s date → book e.g. 10:00–11:00.
3. Open an **incognito** window, register another user (or use a second account).
4. Try the **same** space and overlapping time → UI shows **409 Conflict**.

CLI / curl (two shells racing):

```bash
TOKEN_A=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -d 'username=student@slotlock.local&password=student123' | jq -r .access_token)
# register second user, get TOKEN_B, then:
curl -s -o /tmp/a.json -w "%{http_code}" -X POST http://localhost:8000/api/reservations \
  -H "Authorization: Bearer $TOKEN_A" -H 'Content-Type: application/json' \
  -d '{"space_id":1,"start_at":"2026-09-16T10:00:00+09:00","end_at":"2026-09-16T11:00:00+09:00"}'
```

Automated proof:

```bash
cd backend && pytest -v
# includes concurrent ThreadPool: exactly one 201, two 409, one DB row
```

---

## Tests

```bash
cd /workspace/slotlock/backend
export TEST_DATABASE_URL=postgresql+psycopg2://slotlock:slotlock@localhost:5432/slotlock_test
export REDIS_ENABLED=false
pytest -v
```

Coverage:

- Exact / partial overlap → 409  
- Adjacent half-open `[10,11)` + `[11,12)` → both 201  
- Cancel frees slot  
- Early check-out (checked-in → completed) frees the remaining time for others to book  
- Different spaces may overlap  
- **Concurrency:** 3 parallel bookings → 1 success, 2×409, no duplicate rows  

---

## Migrations

```bash
cd backend
alembic upgrade head
# revision 001: users, spaces, reservations + excl_no_overlap_active
# revision 002: app_settings (admin-tunable business rules)
# revision 003: reservations.party_size
```

API lifespan also runs `CREATE EXTENSION btree_gist`, `create_all`, and seed if empty (convenient for demos).

**Gotcha:** `create_all` only creates *missing tables* — it never `ALTER`s a table that already exists. So a running dev DB that was bootstrapped by `create_all` (the docker-compose flow above) needs `alembic upgrade head` run against it (or a manual `ALTER TABLE`) whenever a migration adds a column to an existing table, e.g. `party_size` in 003 or `is_admin_block` in 004. A brand-new table (like `app_settings` in 002) is unaffected since `create_all` does create those.

---

## Stretch features included

- Redis cache for slot queries  
- Daily 2-hour booking limit  
- Check-in endpoint + admin `POST /api/admin/run-no-show-worker` (marks overdue confirmed → `no_show`)  
- Check-out endpoint (`POST /api/reservations/{id}/check-out`): ends a checked-in reservation early (status → `completed`), immediately freeing the remaining time for others to book  
- Basic admin: `GET /api/admin/stats`, `POST /api/spaces` (admin JWT)  
- Runtime-editable business rules (`GET /api/admin/settings`, admin-only `PUT /api/admin/settings`): daily booking limit, slot size, check-in grace period — persisted in `app_settings`, with an admin-only **관리자 설정** page in the frontend (`/admin/settings`)  
- Party size per reservation (`party_size`, capped by the space's capacity) and an admin **예약 현황** dashboard (`/admin/reservations`, `GET /api/admin/reservations?date=&space_id=`): who booked what with how many people ("OOO 외 N명"), with one-click admin cancel on any reservation  
- Admin time-blocking (`POST /api/admin/blocks`): an admin picks a slot range on a space and blocks it off with a reason (e.g. a school class) instead of making a real booking — reuses the same exclusion-constraint/slot-availability machinery so a block still prevents double-booking, but skips the per-user daily-hour limit and party size, and is excluded from the blocking admin's own "내 예약" list  

## Out of scope / follow-ups

Payments, SSO, mobile apps, SMS, floor plans, Jenkins / SonarQube / Grafana / JMeter full stacks — suitable next milestones for the course report.

---

## License

Course project — A+ 원정대, CSE4022.
