"""CLI: python -m scripts.seed  (run from backend/ with PYTHONPATH=.)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.database import Base, SessionLocal, engine
from app.scripts.seed import seed_if_empty

if __name__ == "__main__":
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
        Base.metadata.create_all(bind=conn)
    db = SessionLocal()
    try:
        seed_if_empty(db)
        print("Seed complete.")
    finally:
        db.close()
