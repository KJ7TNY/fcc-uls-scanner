#!/usr/bin/env python3
"""
Reload FR (Frequency) table with CORRECT column mapping.
Confirmed column positions from actual FR.dat data:
  col  1 = record_type
  col  2 = unique_system_id
  col  3 = uls_file_number
  col  4 = ebf_number
  col  5 = call_sign
  col  6 = location_number
  col  7 = antenna_number
  col  8 = class_station_code (location class)
  col  9 = station_class  (FB2, MO, FX etc)  ← KEY
  col 10 = op_altitude_code
  col 11 = frequency  (MHz)                  ← KEY
  col 12 = frequency_assigned
  col 13 = frequency_upper_band
  col 14 = frequency_offset
  col 15 = frequency_channel
  col 16 = power_erp  (watts)                ← KEY
  col 17 = eirp
  col 18 = tolerance
  col 19 = frequency_ind
  col 20 = status_code
  col 21 = status_date
  col 22 = col22
  col 23 = col23
  col 24 = col24
  col 25 = col25
  col 26 = col26
  col 27 = col27
  col 28 = col28
  col 29 = col29
  col 30 = col30

Usage:
    python3 reload_fr.py
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

    print("\n  Rebuilding FR (Frequency) table with correct columns...")

    con.executescript("""
        DROP TABLE IF EXISTS fr;
        CREATE TABLE fr (
            record_type          TEXT,
            unique_system_id     TEXT,
            uls_file_number      TEXT,
            ebf_number           TEXT,
            call_sign            TEXT,
            location_number      TEXT,
            antenna_number       TEXT,
            class_station_code   TEXT,
            station_class        TEXT,
            op_altitude_code     TEXT,
            frequency            REAL,
            frequency_assigned   REAL,
            frequency_upper_band REAL,
            frequency_offset     TEXT,
            frequency_channel    TEXT,
            power_erp            REAL,
            eirp                 REAL,
            tolerance            REAL,
            frequency_ind        TEXT,
            status_code          TEXT,
            status_date          TEXT,
            col22                TEXT,
            col23                TEXT,
            col24                TEXT,
            col25                TEXT,
            col26                TEXT,
            col27                TEXT,
            col28                TEXT,
            col29                TEXT,
            col30                TEXT
        );
        CREATE INDEX idx_fr_sysid ON fr(unique_system_id);
        CREATE INDEX idx_fr_freq  ON fr(frequency);
    """)
    con.commit()
    print("  ✓ FR table recreated with correct column order")

    filepath = os.path.join(DAT_FOLDER, "FR.dat")
    if not os.path.exists(filepath):
        print(f"  ⚠  FR.dat not found in {DAT_FOLDER}")
        return

    print("  Loading FR.dat ...", end="", flush=True)
    rows = []
    with open(filepath, encoding="latin-1", errors="replace") as f:
        for line in f:
            parts = line.rstrip("\n\r").split("|")
            if len(parts) < 30:
                parts += [""] * (30 - len(parts))
            parts = parts[:30]
            rows.append(parts)

            if len(rows) >= 50000:
                con.executemany(
                    "INSERT INTO fr VALUES (" + ",".join(["?"]*30) + ")",
                    rows
                )
                con.commit()
                rows = []

    if rows:
        con.executemany(
            "INSERT INTO fr VALUES (" + ",".join(["?"]*30) + ")",
            rows
        )
        con.commit()

    count = con.execute("SELECT COUNT(*) FROM fr").fetchone()[0]
    print(f" ✓  {count:,} frequency records loaded")

    # Verify it worked
    print("\n  Verification (should show freq=47.94 / class=FB2 / power=150.0):")
    test = con.execute("""
        SELECT unique_system_id, frequency, station_class, power_erp
        FROM fr WHERE unique_system_id = '835774' LIMIT 5
    """).fetchall()

    for row in test:
        print(f"    sys_id={row[0]}  freq={row[1]}  class={row[2]}  power={row[3]}")

    con.execute("ANALYZE")
    con.close()
    print("\n  ✓  Done! Run search_fcc.py to see full frequency data!\n")

if __name__ == "__main__":
    main()
