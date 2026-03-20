#!/usr/bin/env python3
"""
Add EM (Emission) table to existing FCC database.
Run this ONCE after import_fcc.py has already finished.
It adds emission designators without re-importing everything.

Usage:
    python3 add_em.py
"""

import sqlite3
import os

DAT_FOLDER = os.path.expanduser("~/fcc-scanner/data")
DB_PATH    = os.path.expanduser("~/fcc-scanner/fcc.db")

def main():
    if not os.path.exists(DB_PATH):
        print("⚠  Database not found! Run import_fcc.py first.")
        return

    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")

    print("\n  Adding EM (Emission Designator) table...")

    con.executescript("""
        DROP TABLE IF EXISTS em;
        CREATE TABLE em (
            record_type         TEXT,
            unique_system_id    TEXT,
            uls_file_number     TEXT,
            ebf_number          TEXT,
            call_sign           TEXT,
            location_number     INTEGER,
            antenna_number      INTEGER,
            frequency           REAL,
            status_code         TEXT,
            emission_designator TEXT,
            digital_output_code TEXT,
            digital_output_rate TEXT,
            emission_seq_id     INTEGER,
            col14               TEXT,
            col15               TEXT,
            col16               TEXT
        );
        CREATE INDEX idx_em_sysid ON em(unique_system_id);
        CREATE INDEX idx_em_freq  ON em(frequency);
    """)
    con.commit()
    print("  ✓ EM table created")

    filepath = os.path.join(DAT_FOLDER, "EM.dat")
    if not os.path.exists(filepath):
        print(f"  ⚠  EM.dat not found in {DAT_FOLDER}")
        return

    print("  Loading EM.dat ...", end="", flush=True)
    rows = []
    with open(filepath, encoding="latin-1", errors="replace") as f:
        for line in f:
            parts = line.rstrip("\n\r").split("|")
            if len(parts) < 16:
                parts += [""] * (16 - len(parts))
            parts = parts[:16]
            rows.append(parts)

            if len(rows) >= 50000:
                con.executemany(
                    "INSERT INTO em VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    rows
                )
                con.commit()
                rows = []

    if rows:
        con.executemany(
            "INSERT INTO em VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            rows
        )
        con.commit()

    count = con.execute("SELECT COUNT(*) FROM em").fetchone()[0]
    print(f" ✓  {count:,} emission records loaded")

    con.execute("ANALYZE")
    con.close()

    print("\n  ✓  Done! Now run search_fcc.py to see frequencies with emission designators!\n")

if __name__ == "__main__":
    main()
