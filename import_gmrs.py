#!/usr/bin/env python3
"""
FCC GMRS License Database Importer
====================================
Imports the FCC GMRS (General Mobile Radio Service) database
into fcc.db as a 'gmrs' table for offline callsign lookup.

Downloads from:
    https://data.fcc.gov/download/pub/uls/complete/l_gmrs.zip

Unzip into ~/fcc-scanner/gmrs/ then run this script.

GMRS Facts:
    - No test required — just pay $35 to FCC
    - One license covers entire family!!
    - 10 year license term
    - Callsign format: WRZXXXX
    - Covers 462/467 MHz repeater and simplex channels
    - Very popular in rural and outdoor communities

Usage:
    python3 import_gmrs.py

Update anytime by re-downloading l_gmrs.zip and running again.
"""

import sqlite3
import os
import sys

DB_PATH     = os.path.expanduser("~/fcc-scanner/fcc.db")
GMRS_FOLDER = os.path.expanduser("~/fcc-scanner/gmrs")

# Status decoder
STATUS_DECODE = {
    "A": "Active",
    "C": "Cancelled",
    "E": "Expired",
    "T": "Terminated",
    "":  "Unknown",
}

def main():
    if not os.path.exists(DB_PATH):
        print("⚠  fcc.db not found! Run import_fcc.py first.")
        sys.exit(1)

    for f in ["HD.dat", "EN.dat"]:
        if not os.path.exists(os.path.join(GMRS_FOLDER, f)):
            print(f"⚠  {f} not found in {GMRS_FOLDER}")
            print("   Unzip l_gmrs.zip into ~/fcc-scanner/gmrs/ first!")
            sys.exit(1)

    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")

    print(f"\n{'='*55}")
    print("  FCC GMRS License Database Importer")
    print(f"{'='*55}")
    print(f"  Source : {GMRS_FOLDER}")
    print(f"  Output : {DB_PATH}")
    print(f"{'='*55}\n")

    # Create gmrs table
    con.executescript("""
        DROP TABLE IF EXISTS gmrs;
        CREATE TABLE gmrs (
            unique_system_id  TEXT,
            call_sign         TEXT,
            status            TEXT,
            status_desc       TEXT,
            grant_date        TEXT,
            expired_date      TEXT,
            effective_date    TEXT,
            full_name         TEXT,
            first_name        TEXT,
            last_name         TEXT,
            address           TEXT,
            city              TEXT,
            state             TEXT,
            zip_code          TEXT,
            frn               TEXT
        );
        CREATE INDEX idx_gmrs_callsign ON gmrs(call_sign);
        CREATE INDEX idx_gmrs_name     ON gmrs(UPPER(last_name));
        CREATE INDEX idx_gmrs_frn      ON gmrs(frn);
        CREATE INDEX idx_gmrs_state    ON gmrs(state);
        CREATE INDEX idx_gmrs_status   ON gmrs(status);
    """)
    con.commit()
    print("✓ GMRS table created")

    # Step 1: Load HD - get call signs, status, dates
    print("  Loading HD.dat ...", end="", flush=True)
    hd = {}
    with open(os.path.join(GMRS_FOLDER, "HD.dat"), encoding="latin-1") as f:
        for line in f:
            parts = line.rstrip("\n\r").split("|")
            if len(parts) < 10:
                parts += [""] * (10 - len(parts))
            sysid          = parts[1].strip()
            callsign       = parts[4].strip()
            status         = parts[5].strip()
            grant_date     = parts[7].strip()
            expired_date   = parts[8].strip()
            effective_date = parts[9].strip()
            if callsign:
                hd[sysid] = {
                    "call_sign":      callsign,
                    "status":         status,
                    "status_desc":    STATUS_DECODE.get(status, status),
                    "grant_date":     grant_date,
                    "expired_date":   expired_date,
                    "effective_date": effective_date,
                }
    print(f" ✓  {len(hd):,} licenses")

    # Step 2: Load EN - get name and address
    print("  Loading EN.dat ...", end="", flush=True)
    en = {}
    with open(os.path.join(GMRS_FOLDER, "EN.dat"), encoding="latin-1") as f:
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
            en[sysid] = {
                "full_name":  full_name,
                "first_name": first_name,
                "last_name":  last_name,
                "address":    address,
                "city":       city,
                "state":      state,
                "zip_code":   zip_code,
                "frn":        frn,
            }
    print(f" ✓  {len(en):,} entities")

    # Step 3: Merge and insert
    print("  Building GMRS table  ...", end="", flush=True)
    rows = []
    active = expired = other = 0

    for sysid, h in hd.items():
        e = en.get(sysid, {})

        if h["status"] == "A":
            active += 1
        elif h["status"] == "E":
            expired += 1
        else:
            other += 1

        rows.append((
            sysid,
            h.get("call_sign", ""),
            h.get("status", ""),
            h.get("status_desc", ""),
            h.get("grant_date", ""),
            h.get("expired_date", ""),
            h.get("effective_date", ""),
            e.get("full_name", ""),
            e.get("first_name", ""),
            e.get("last_name", ""),
            e.get("address", ""),
            e.get("city", ""),
            e.get("state", ""),
            e.get("zip_code", ""),
            e.get("frn", ""),
        ))

        if len(rows) >= 50000:
            con.executemany(
                "INSERT INTO gmrs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                rows
            )
            con.commit()
            rows = []

    if rows:
        con.executemany(
            "INSERT INTO gmrs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            rows
        )
        con.commit()

    count = con.execute("SELECT COUNT(*) FROM gmrs").fetchone()[0]
    print(f" ✓  {count:,} GMRS licenses loaded")

    con.execute("ANALYZE")
    con.close()

    print(f"\n{'='*55}")
    print(f"  ✓  Done!")
    print(f"{'='*55}")
    print(f"  Active    : {active:,}")
    print(f"  Expired   : {expired:,}")
    print(f"  Other     : {other:,}")
    print(f"  Total     : {count:,}")
    print(f"{'='*55}")
    print("\n  HamCall now supports GMRS lookup!!")
    print("  Try looking up a GMRS callsign!!\n")


if __name__ == "__main__":
    main()
