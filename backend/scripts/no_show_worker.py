"""Simple polling worker: mark missed check-ins as no_show.

  PYTHONPATH=. python scripts/no_show_worker.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.services.reservations import auto_cancel_no_shows


def main(interval: int = 60):
    print(f"No-show worker started (interval={interval}s)")
    while True:
        db = SessionLocal()
        try:
            n = auto_cancel_no_shows(db)
            if n:
                print(f"marked {n} reservation(s) as no_show")
        finally:
            db.close()
        time.sleep(interval)


if __name__ == "__main__":
    main()
