#!/usr/bin/env python3
"""
FCC Amateur Radio Callsign Database Importer
=============================================
Imports the FCC Amateur Radio database into fcc.db
as an 'amateur' table for offline ham callsign lookup.

Downloads from:
    https://data.fcc.gov/download/pub/uls/complete/a_amat.zip

Unzip into ~/fcc-scanner/amateur/ then run this script.

Usage:
    python3 import_amateur.py

Update anytime by re-downloading a_amat.zip and running again.
"""

import sqlite3
import os
import sys

DB_PATH     = os.path.expanduser("~/fcc-scanner/fcc.db")
AMAT_FOLDER = os.path.expanduser("~/fcc-scanner/amateur")

OPERATOR_CLASS = {
    "A": "Advanced",
    "B": "Technician Plus",
    "C": "Amateur Extra",
    "D": "Technician",
    "E": "Amateur Extra",
    "G": "General",
    "N": "Novice",
    "T": "Technician",
    "P": "Technician Plus",
    "":  "General",
}

def main():
    if not os.path.exists(DB_PATH):
        print("⚠  fcc.db not found! Run import_fcc.py first.")
        sys.exit(1)

    for f in ["HD.dat", "EN.dat", "AM.dat"]:
        if not os.path.exists(os.path.join(AMAT_FOLDER, f)):
            print(f"⚠  {f} not found in {AMAT_FOLDER}")
            print("   Unzip a_amat.zip into ~/fcc-scanner/amateur/ first!")
            sys.exit(1)

    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute("PRAGMA cache_size=-64000")  # 64MB cache

    print(f"\n{'='*55}")
    print("  FCC Amateur Radio Database Importer")
    print(f"{'='*55}")
    print(f"  Source : {AMAT_FOLDER}")
    print(f"  Output : {DB_PATH}")
    print(f"{'='*55}\n")

    # Create amateur table
    con.executescript("""
        DROP TABLE IF EXISTS amateur;
        CREATE TABLE amateur (
            unique_system_id  TEXT PRIMARY KEY,
            call_sign         TEXT,
            status            TEXT,
            grant_date        TEXT,
            expired_date      TEXT,
            full_name         TEXT,
            first_name        TEXT,
            last_name         TEXT,
            address           TEXT,
            city              TEXT,
            state             TEXT,
            zip_code          TEXT,
            frn               TEXT,
            operator_class    TEXT,
            class_code        TEXT,
            group_code        TEXT
        );
    """)
    con.commit()
    print("✓ Amateur table created")

    # Step 1: Load HD only into memory (small fields only)
    print("  Loading HD.dat ...", end="", flush=True)
    hd = {}
    with open(os.path.join(AMAT_FOLDER, "HD.dat"), encoding="latin-1") as f:
        for line in f:
            parts = line.rstrip("\n\r").split("|")
            if len(parts) < 44:
                parts += [""] * (44 - len(parts))
            sysid      = parts[1].strip()
            callsign   = parts[4].strip()
            status     = parts[6].strip()
            grant_date = parts[43].strip() if len(parts) > 43 else ""
            exp_date   = parts[8].strip()  if len(parts) > 8  else ""
            if callsign:
                hd[sysid] = (callsign, status, grant_date, exp_date)
    print(f" ✓  {len(hd):,} licenses")

    # Step 2: Stream EN.dat and insert merged rows immediately
    # This avoids holding EN in memory
    print("  Loading EN.dat and inserting ...", end="", flush=True)
    rows = []
    count_en = 0
    with open(os.path.join(AMAT_FOLDER, "EN.dat"), encoding="latin-1") as f:
        for line in f:
            parts = line.rstrip("\n\r").split("|")
            if len(parts) < 24:
                parts += [""] * (24 - len(parts))
            sysid      = parts[1].strip()
            full_name  = parts[7].strip()
            first_name = parts[8].strip()
            last_name  = parts[10].strip()
            address    = parts[15].strip()
            city       = parts[16].strip()
            state      = parts[17].strip()
            zip_code   = parts[18].strip()
            frn        = parts[22].strip()

            h = hd.get(sysid)
            if not h:
                continue

            callsign, status, grant_date, exp_date = h
            rows.append((
                sysid, callsign, status, grant_date, exp_date,
                full_name, first_name, last_name, address,
                city, state, zip_code, frn,
                "General", "", ""  # class filled in next pass
            ))
            count_en += 1

            if len(rows) >= 50000:
                con.executemany(
                    "INSERT OR REPLACE INTO amateur VALUES "
                    "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    rows
                )
                con.commit()
                rows = []

    if rows:
        con.executemany(
            "INSERT OR REPLACE INTO amateur VALUES "
            "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            rows
        )
        con.commit()

    # Free HD from memory now
    del hd
    print(f" ✓  {count_en:,} records inserted")

    # Step 3: Stream AM.dat and UPDATE class codes
    print("  Loading AM.dat and updating classes ...", end="", flush=True)
    count_am = 0
    updates = []
    with open(os.path.join(AMAT_FOLDER, "AM.dat"), encoding="latin-1") as f:
        for line in f:
            parts = line.rstrip("\n\r").split("|")
            if len(parts) < 9:
                parts += [""] * (9 - len(parts))
            sysid      = parts[1].strip()
            class_code = parts[5].strip()
            group_code = parts[7].strip()
            op_class   = OPERATOR_CLASS.get(class_code, class_code)
            updates.append((op_class, class_code, group_code, sysid))
            count_am += 1

            if len(updates) >= 50000:
                con.executemany(
                    "UPDATE amateur SET operator_class=?, class_code=?, "
                    "group_code=? WHERE unique_system_id=?",
                    updates
                )
                con.commit()
                updates = []

    if updates:
        con.executemany(
            "UPDATE amateur SET operator_class=?, class_code=?, "
            "group_code=? WHERE unique_system_id=?",
            updates
        )
        con.commit()
    print(f" ✓  {count_am:,} classes updated")

    # Step 4: Build indexes after data is loaded
    print("  Building indexes ...", end="", flush=True)
    con.executescript("""
        CREATE INDEX IF NOT EXISTS idx_amat_callsign ON amateur(call_sign);
        CREATE INDEX IF NOT EXISTS idx_amat_name     ON amateur(UPPER(last_name));
        CREATE INDEX IF NOT EXISTS idx_amat_frn      ON amateur(frn);
        CREATE INDEX IF NOT EXISTS idx_amat_state    ON amateur(state);
    """)
    con.execute("ANALYZE")
    con.commit()
    print(" ✓")

    count = con.execute("SELECT COUNT(*) FROM amateur").fetchone()[0]
    con.close()

    print(f"\n{'='*55}")
    print(f"  ✓  Done! {count:,} amateur licenses in database")
    print(f"{'='*55}")
    print("  Try looking up your own call sign in HamCall!!\n")


if __name__ == "__main__":
    main()
