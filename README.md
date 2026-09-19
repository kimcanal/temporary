# SlotLock — 서강대학교 스터디룸 예약 MVP

**Team:** A+ 원정대 · **Course:** CSE4022
**Goal:** Prove that concurrent bookings cannot double-book the same space/time using PostgreSQL `EXCLUDE USING gist` (`btree_gist`).

한국어 요약: 스터디룸 예약 시스템 MVP입니다. 동일 공간의 시간 겹침은 DB exclusion constraint로 차단되며, 동시 요청 시 하나만 성공하고 나머지는 HTTP **409 Conflict**를 받습니다.

데모 공간 예시: 곤자가 플라자 스터디룸 A, 로욜라 도서관 그룹룸 3, 다산관 세미나실 B, 엠마오관 회의실 1.

---

## 빠르게 실행하기

```bash
cd slotlock
docker compose up --build
# 구버전 Docker면: docker-compose up --build
```

| 서비스 | 주소 |
|---|---|
| 웹 화면 | http://localhost:3000 |
| API | http://localhost:8000 |
| API 문서(Swagger) | http://localhost:8000/docs |
| Postgres | localhost:5432 (`slotlock` / `slotlock`) |
| Redis | localhost:6379 |

데모 계정 (API 기동 시 자동 시딩):

| 이메일/아이디 | 비밀번호 | 역할 |
|---|---|---|
| `student@slotlock.local` | `student123` | 학생 |
| `admin` | `admin` | 관리자 |

> **WSL2에서 개발 중이라면:** 모든 서비스에 `restart: unless-stopped`가 걸려 있어서 Docker 데몬이 재시작돼도 컨테이너는 알아서 돌아옵니다. WSL VM 자체가 유휴 상태로 꺼졌다면 `cd slotlock && docker compose up -d` 한 번만 다시 실행하면 됩니다. WSL이 자동으로 안 꺼지게 하려면 `%UserProfile%\.wslconfig`의 `[wsl2]`에 `vmIdleTimeout=-1`을 추가하고 `wsl --shutdown` 한 번 해주세요.

Docker 없이 Postgres/Redis를 직접 띄워서 개발하는 방법은 아래 "로컬 개발" 섹션 참고.

---

## 기능 가이드

### 👤 학생(일반 사용자)

- **회원가입 / 로그인** — 이메일 기반 가입, JWT 로그인
- **공간 목록 / 상세 조회** — 위치, 정원, 운영시간 확인
- **날짜별 예약 가능 슬롯 조회** — 30분 단위(관리자가 바꾸면 그 값) 슬롯을 오전/오후로 나눠서 표시
- **슬롯 예약** — 시작 슬롯 클릭 → 끝 슬롯 클릭하면 그 사이가 자동으로 선택됨(한 칸씩 클릭할 필요 없음). 이용 인원도 같이 입력(공간 정원 이내로 제한). 하루 예약 가능 시간(기본 2시간)을 넘으면 거부됨
- **내 예약 목록** — 상태별(확정/체크인/완료/취소/노쇼) 확인, 인원수 같이 표시
- **체크인** — 예약 시작 시각 앞뒤 유예시간(기본 15분) 안에서만 가능
- **조기 퇴실** — 체크인한 예약을 일찍 끝내서, 남은 시간을 다른 사람이 바로 예약할 수 있게 풀어줌
- **예약 취소**

### 🛠 관리자 (학생 기능 전부 + 아래 추가)

관리자로 로그인하면 상단 네비게이션에 **관리자 설정**, **예약 현황** 메뉴가 추가로 보입니다.

- **관리자 설정** (`/admin/settings`) — 하루 예약 한도(시간), 슬롯 단위(30분/1시간), 체크인 유예 시간을 실시간으로 변경. 서버 재배포 없이 바로 모든 사용자에게 적용됨
- **예약 현황 대시보드** (`/admin/reservations`) — 날짜·공간별로 전체 예약을 한눈에 조회. 예약자 이름과 인원("OOO 외 N명")이 보이고, 어떤 예약이든 임의로 취소 가능
- **시간대 차단** — 공간 상세 페이지에서 슬롯 구간을 고르고 사유(예: "학교 수업")를 적어 차단. 실제 예약처럼 그 시간대를 막아버리지만(다른 사람은 예약 불가), 일반 예약과는 다르게 취급됨:
  - 차단을 건 관리자 본인의 하루 이용 한도에는 포함되지 않음
  - 체크인하지 않았다고 자동으로 "노쇼" 처리되어 슬롯이 풀리는 일이 없음 (수업이 진행 중인데 15분 뒤에 저절로 예약 가능 상태로 바뀌는 버그를 방지)
  - 관리자 본인의 "내 예약" 목록에는 안 뜸(개인 예약이 아니므로)
- **공간 생성** (`POST /api/spaces`) — 현재는 API로만 가능, 화면은 아직 없음

### ⚙️ 시스템이 자동으로 처리하는 것

- **노쇼 자동 처리** — 체크인 유예 시간이 지나도록 체크인 안 하면 자동으로 "노쇼"로 바뀌고 슬롯이 반환됨 (`backend/scripts/no_show_worker.py`를 주기적으로 돌리거나, 관리자가 `POST /api/admin/run-no-show-worker`로 수동 실행)
- **캐시 자동 갱신** — 예약 생성/취소/체크인/체크아웃/차단 등 상태가 바뀔 때마다 해당 공간의 슬롯 캐시(Redis)를 자동으로 지워서, 방금 예약한 슬롯이 캐시 때문에 계속 "예약 가능"으로 보이는 일이 없게 함

---

## 아키텍처

```
React (Vite) ──JWT──▶ FastAPI ──SQLAlchemy──▶ PostgreSQL 16
                         │                      └ EXCLUDE USING gist
                         └── Redis (slot cache, optional)
```

| 계층 | 역할 |
|---|---|
| **Auth** | 회원가입/로그인, JWT bearer (`/api/auth/*`) |
| **Spaces** | 목록/상세 조회, 관리자 생성, 날짜별 슬롯 |
| **Reservations** | 생성/취소/체크인/체크아웃/내 예약 |
| **Admin** | 설정 변경, 예약 현황, 시간대 차단 (`/api/admin/*`) |
| **DB 불변식** | `EXCLUDE USING gist (space_id WITH =, tstzrange(start_at,end_at,'[)') WITH &&) WHERE status IN ('confirmed','checked_in')` |
| **Cache** | `GET /spaces/{id}/slots` 결과를 Redis에 TTL 15초로 캐싱 (Redis 다운되면 캐시 없이 정상 동작) |

모듈 구조(`backend/app/`): `api/`, `core/`, `models/`, `schemas/`, `services/`, `scripts/`.

---

## 동시성(Concurrency) 처리

이 프로젝트의 핵심은 "여러 요청을 동시에 받는 것"과 "데이터가 꼬이지 않는 것"을 구분해서 다루는 데 있습니다.

- **여러 요청 동시 처리**: uvicorn(uvloop)이 비동기 이벤트 루프로 다중 연결을 받고, 동기 핸들러(DB I/O가 blocking이라)는 스레드풀에 위임됨
- **이중예약 방지**: PostgreSQL `EXCLUDE USING gist` 제약이 DB 레벨에서 원자적으로 처리 — 두 요청이 정확히 동시에 INSERT해도 하나만 성공하고 나머지는 `IntegrityError` → API가 409로 변환
- **하루 이용 한도 레이스**: DB 제약만으로는 못 막는 경우(겹치지 않는 다른 시간대 두 건을 동시에 예약)라서, `pg_advisory_xact_lock(user_id)`로 같은 유저의 예약 생성 트랜잭션을 직렬화
- **취소/체크인/체크아웃 동시 조작**: `SELECT ... FOR UPDATE`로 행 잠금을 걸어서 lost-update 방지

`test_concurrency.py`에서 여러 스레드가 실제로 같은 API를 동시에 때리는 방식으로 검증합니다.

---

## 409 충돌 데모

1. `student@slotlock.local`로 로그인
2. 공간 하나 열고 → 내일 날짜 → 예: 10:00–11:00 예약
3. 시크릿 창으로 다른 계정 로그인
4. **같은 공간·겹치는 시간**으로 예약 시도 → 화면에 **409 Conflict**

CLI로 확인(터미널 두 개로 경쟁):

```bash
TOKEN_A=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -d 'username=student@slotlock.local&password=student123' | jq -r .access_token)
# 두 번째 유저 등록 후 TOKEN_B 받아서:
curl -s -o /tmp/a.json -w "%{http_code}" -X POST http://localhost:8000/api/reservations \
  -H "Authorization: Bearer $TOKEN_A" -H 'Content-Type: application/json' \
  -d '{"space_id":1,"start_at":"2026-09-20T10:00:00+09:00","end_at":"2026-09-20T11:00:00+09:00"}'
```

자동 증명:

```bash
cd backend && pytest -v
# 여러 스레드가 동시에 같은 슬롯을 예약 → 201 하나, 409 나머지, DB엔 중복 행 없음
```

---

## 테스트

```bash
cd backend
export TEST_DATABASE_URL=postgresql+psycopg2://slotlock:slotlock@localhost:5432/slotlock_test
export REDIS_ENABLED=false
pytest -v
```

커버리지(31개 케이스):

- 겹침/부분 겹침 → 409, 인접 half-open 슬롯 → 둘 다 201
- 취소/조기 퇴실이 슬롯을 실제로 반환하는지
- **동시성**: 여러 스레드 동시 예약 → 1건만 성공, 하루 한도 레이스도 재현·검증
- 관리자 설정 변경이 실제 예약 로직에 즉시 반영되는지
- 인원수(정원 초과 거부), 관리자 예약 현황 목록
- 관리자 시간대 차단(이중예약 방지, 본인 한도 미포함, 노쇼 미대상, 체크인 불가)

---

## 마이그레이션

```bash
cd backend
alembic upgrade head
# 001: users, spaces, reservations + excl_no_overlap_active
# 002: app_settings (관리자가 바꿀 수 있는 운영 규칙)
# 003: reservations.party_size
# 004: reservations.is_admin_block
```

API 기동 시 `CREATE EXTENSION btree_gist` → `create_all` → 비어있으면 시드 데이터 생성까지 자동으로 실행됩니다(데모 편의용).

**주의:** `create_all`은 **없는 테이블만** 만들고, 이미 있는 테이블에 컬럼을 추가해주지 않습니다. 그래서 `create_all`로 이미 떠 있던 개발 DB에 새 컬럼이 추가되는 마이그레이션(003, 004)이 생기면, 그 DB엔 `alembic upgrade head`를 따로 돌리거나 수동 `ALTER TABLE`이 필요합니다. 새 테이블(002의 `app_settings`)은 `create_all`이 알아서 만들어주므로 상관없습니다.

---

## 로컬 개발 (Docker 없이, Postgres/Redis는 이미 떠 있다고 가정)

```bash
# 백엔드
cd backend
python -m venv ../../slotlock-venv && source ../../slotlock-venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg2://slotlock:slotlock@localhost:5432/slotlock
export REDIS_URL=redis://localhost:6379/0
export PYTHONPATH=.
alembic upgrade head   # 또는 기동 시 create_all + seed에 맡겨도 됨
python scripts/seed.py
uvicorn app.main:app --reload --port 8000

# 프론트엔드 (다른 터미널)
cd frontend
npm install && npm run dev
# → http://localhost:5173
```

`.env.example`을 `.env`로 복사해서 필요하면 값을 바꾸세요.

---

## 범위 밖 / 다음 단계

Payments, SSO, 모바일 앱, SMS, 좌석 배치도, 공간 운영시간 수정 화면, 공간별 이용률 통계, Jenkins / SonarQube / Prometheus·Grafana / Loki / JMeter — 과제 계획서(팀 R&R)상 이후 주차에 다룰 항목들입니다.

---

## License

Course project — A+ 원정대, CSE4022.
