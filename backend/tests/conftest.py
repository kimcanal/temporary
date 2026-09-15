"""Pytest fixtures – use dedicated test database."""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Force test DB before app imports settings cache
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://slotlock:slotlock@localhost:5432/slotlock_test",
)
os.environ["REDIS_ENABLED"] = "false"
os.environ["SECRET_KEY"] = "test-secret-key-for-pytest-slotlock"

from app.config import get_settings

get_settings.cache_clear()

from app.database import Base, get_db
from app.main import create_app
from app.models import AppSettings, Reservation, Space, User  # noqa: F401
from app.core.security import hash_password
from datetime import time


TEST_URL = os.environ["DATABASE_URL"]
engine = create_engine(TEST_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def prepare_db():
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
        conn.execute(text("DROP TABLE IF EXISTS reservations CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS spaces CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS app_settings CASCADE"))
        Base.metadata.create_all(bind=conn)
    yield
    with engine.begin() as conn:
        Base.metadata.drop_all(bind=conn)


@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    # Nested savepoint so app commits don't escape
    session.begin_nested()

    @pytest.fixture  # noqa – marker unused; keep session clean via truncates below
    def _noop():
        pass

    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    # Truncate between tests for isolation (exclusion constraint needs real commits)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE reservations, spaces, users, app_settings RESTART IDENTITY CASCADE"))

    # Seed space + users outside request
    session = TestingSessionLocal()
    space = Space(
        name="Test Room",
        description="pytest",
        capacity=4,
        location="Lab",
        open_time=time(9, 0),
        close_time=time(22, 0),
    )
    u1 = User(email="u1@test.com", hashed_password=hash_password("pass1234"), full_name="User One")
    u2 = User(email="u2@test.com", hashed_password=hash_password("pass1234"), full_name="User Two")
    u3 = User(email="u3@test.com", hashed_password=hash_password("pass1234"), full_name="User Three")
    session.add_all([space, u1, u2, u3])
    session.commit()
    space_id = space.id
    session.close()

    app = create_app()

    def _override():
        s = TestingSessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        c.space_id = space_id  # type: ignore[attr-defined]
        yield c
    app.dependency_overrides.clear()


def auth_header(client: TestClient, email: str, password: str = "pass1234") -> dict:
    r = client.post(
        "/api/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
