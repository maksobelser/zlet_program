# backend/seed.py

import csv
from sqlmodel import SQLModel, create_engine, Session
from passlib.context import CryptContext
from sqlalchemy import text

import config, models

# ─── password hasher ─────────────────────────────────────────────────────────────
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ─── create engine ──────────────────────────────────────────────────────────────
engine = create_engine(config.settings.database_url, echo=True)

# ─── drop & recreate everything ─────────────────────────────────────────────────
with engine.begin() as conn:
    # Option A: drop all tables known to SQLModel
    SQLModel.metadata.drop_all(conn)

    # Option B (more drastic—uncomment if you want a totally clean schema):
    # conn.execute(text("DROP SCHEMA public CASCADE"))
    # conn.execute(text("CREATE SCHEMA public"))

    # recreate tables based on your current models.py
    SQLModel.metadata.create_all(conn)
    print("✅ Tables dropped and recreated")

# ─── seed CSV data ─────────────────────────────────────────────────────────────
with Session(engine) as session:
    # users.csv → User
    with open("users.csv", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            session.add(models.User(
                email=row["username"],
                hashed_password=pwd.hash(row["pass_clanska"]),
                name=row["Ime"],
                surname=row["priimek"],
                leader=row["vodnik"] == "1",
                group=row["vod"],
                age=row["starost"],
                can_apply_early=row["Prednost izbire"] == "1",
                is_active=True,
                is_superuser=False,
                is_verified=True,
            ))

    # trails.csv → Trail  (ONLY name, description, max_applicants)
    with open("trails.csv", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            session.add(models.Trail(
                name=row["name"],
                description=row["description"],
                max_applicants=int(row["max_applicants"]),
            ))

    session.commit()
    print("✅ CSV data imported and committed")

print("🎉 Dev seed complete: schema reset and data reloaded.")