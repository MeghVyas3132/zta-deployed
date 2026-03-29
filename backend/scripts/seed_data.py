from __future__ import annotations

from app.db.models import Base
from app.db.session import SessionLocal, engine
from scripts.ipeds_import import seed_ipeds_demo


def seed() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Legacy Campus A / Campus B sample seed has been intentionally disabled.
        # The app now boots against the imported IPEDS dataset only.
        seeded = seed_ipeds_demo(db)
        db.commit()
        print(f"Seed completed with {seeded} IPEDS institutions")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
