# backend/seed.py

import csv
from sqlmodel import SQLModel, create_engine, Session
from passlib.context import CryptContext
from sqlalchemy import text

drop_tables = True  # Set to False if you want to keep existing tables

import config, models

# ─── password hasher ─────────────────────────────────────────────────────────────
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ─── create engine ──────────────────────────────────────────────────────────────
engine = create_engine(config.settings.database_url, echo=True)

if drop_tables:
    print("🔄 Dropping and recreating just the tables in question...")
    from models import MorningActivity, AfternoonActivity, ApplicationsMorningActivity, ApplicationsAfternoonActivity, SeasideDay

    # only drop & recreate the two tables we seed
    tables = [MorningActivity.__table__, AfternoonActivity.__table__, ApplicationsMorningActivity.__table__, ApplicationsAfternoonActivity.__table__, SeasideDay.__table__]

    with engine.begin() as conn:
        # drop only those tables
        for tbl in tables:
            print(f"Dropping table: {tbl.name}")
            tbl.drop(conn, checkfirst=True)

        # recreate only those tables
        for tbl in tables:
            print(f"Recreating table: {tbl.name}")
            tbl.create(conn, checkfirst=True)

    print("✅ Selected tables dropped and recreated")

# ─── seed CSV data ─────────────────────────────────────────────────────────────
with Session(engine) as session:

    # dop_program.csv → MorningActivity  
    with open("./seed_data_vol_2/dop_program.csv", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            session.add(models.MorningActivity(
                name=row["name"],
                description=row["description"],
                max_participants=int(row["max_applicants"]),
                english_language=row["english_language"] == "1",
                older_participants=row["older_participants"] == "1",
                day=row["day"] or None,
                theme = row.get("theme", None)
            ))

    # pop_program.csv → AfternoonActivity  
    with open("./seed_data_vol_2/pop_program.csv", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            session.add(models.AfternoonActivity(
                name=row["name"],
                description=row["description"],
                max_participants=int(row["max_applicants"]),
                english_language=row["english_language"] == "1",
                older_participants=row["older_participants"] == "1",
                day=row["day"] or None
            ))

    # pop_program.csv → AfternoonActivity  
    with open("./seed_data_vol_2/morje.csv", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            session.add(models.SeasideDay(
                group=row["Vod"],
                day=row["Morje"] or None
            ))

    session.commit()
    print("✅ CSV data imported and committed")

print("🎉 Dev seed complete: selected tables reset and data reloaded.")