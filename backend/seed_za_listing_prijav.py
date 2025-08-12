# backend/seed.py

import csv
from sqlmodel import create_engine, Session
from passlib.context import CryptContext
from models import MorningProgramInfoApplicants, AfternoonProgramInfoApplicants
import config

drop_tables = True  # Set to False if you want to keep existing tables

# ─── password hasher ─────────────────────────────────────────────────────────────
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ─── create engine ──────────────────────────────────────────────────────────────
engine = create_engine(config.settings.database_url, echo=True)

if drop_tables:
    print("🔄 Dropping and recreating just the tables in question...")

    # only drop & recreate the two tables we seed
    tables = [MorningProgramInfoApplicants.__table__, AfternoonProgramInfoApplicants.__table__]

    with engine.begin() as conn:
        # drop only those tables
        for tbl in tables:
            print(f"Dropping table: {tbl.name}")
            tbl.drop(conn, checkfirst=True)

        # recreate only those tables
        for tbl in tables:
            print(f"Recreating table: {tbl.name}")
            tbl.create(conn)

    print("✅ Selected tables dropped and recreated")

# ─── seed CSV data ─────────────────────────────────────────────────────────────
with Session(engine) as session:

    # AfternoonProgramInfoApplicants.csv → ProgramInfoApplicants  
    with open("./seed_data/seed_data_vol_5/AfternoonProgramInfoApplicants.csv", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            session.add(AfternoonProgramInfoApplicants(
                id = int(row["id"]),
                name=row["name"],
                equipment=row["equipment"],
                location = row["location"],
            ))

    # MorningProgramInfoApplicants.csv → MorningProgramInfoApplicants  
    with open("./seed_data/seed_data_vol_5/MorningProgramInfoApplicants.csv", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            session.add(MorningProgramInfoApplicants(
                id = int(row["id"]),
                name=row["name"],
                equipment=row["equipment"],
                location = row["location"],
            ))


    session.commit()
    print("✅ CSV data imported and committed")

print("🎉 Dev seed complete: selected tables reset and data reloaded.")