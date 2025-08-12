# backend/seed.py

import csv
from sqlmodel import create_engine, Session
from passlib.context import CryptContext

drop_tables = True  # Set to False if you want to keep existing tables

import config, models

# ─── password hasher ─────────────────────────────────────────────────────────────
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ─── create engine ──────────────────────────────────────────────────────────────
engine = create_engine(config.settings.database_url, echo=True)

if drop_tables:
    print("🔄 Dropping and recreating just the tables in question...")
    from models import ProgramAddlInfo

    # only drop & recreate the two tables we seed
    tables = [ProgramAddlInfo.__table__]

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
    with open("./seed_data/seed_data_vol_3/ProgramAddlInfo.csv", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            session.add(models.ProgramAddlInfo(
                id = int(row["id"]),
                name=row["name"],
                theme=row["theme"],
                priority = int(float(row["priority"])) if row["priority"] != "" else None,
                category=int(row["category"]),
            ))

    session.commit()
    print("✅ CSV data imported and committed")

print("🎉 Dev seed complete: selected tables reset and data reloaded.")