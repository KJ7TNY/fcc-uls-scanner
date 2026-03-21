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

DB_PATH    = os.path.expanduser("~/fcc-scanner/fcc.db")
AMAT_FOLDER = os.path.expanduser("~/fcc-scanner/amateur")

# Operator class decoder
# FCC AM.dat column 7 codes:
# D = Technician (most common)
# C = Amateur Extra
# A = Advanced
# B = Technician Plus (old)
# E = Extra (old)
# G = General (rarely used in AM.dat)
# N = Novice
# T = Technician (alternate)
# blank = General (many General class have no AM record)
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
            unique_system_id  TEXT,
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
        CREATE INDEX idx_amat_callsign ON amateur(call_sign);
        CREATE INDEX idx_amat_name     ON amateur(UPPER(last_name));
        CREATE INDEX idx_amat_frn      ON amateur(frn);
        CREATE INDEX idx_amat_state    ON amateur(state);
    """)
    con.commit()
    print("✓ Amateur table created")

    # Step 1: Load HD - get call signs and status
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
                hd[sysid] = {
                    "call_sign":    callsign,
                    "status":       status,
                    "grant_date":   grant_date,
                    "expired_date": exp_date,
                }
    print(f" ✓  {len(hd):,} licenses")

    # Step 2: Load EN - get name and address
    print("  Loading EN.dat ...", end="", flush=True)
    en = {}
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

    # Step 3: Load AM - get operator class
    print("  Loading AM.dat ...", end="", flush=True)
    am = {}
    with open(os.path.join(AMAT_FOLDER, "AM.dat"), encoding="latin-1") as f:
        for line in f:
            parts = line.rstrip("\n\r").split("|")
            if len(parts) < 9:
                parts += [""] * (9 - len(parts))
            sysid      = parts[1].strip()
            class_code = parts[5].strip()   # col 6 = current operator class
            group_code = parts[7].strip()   # col 8 = group code
            am[sysid] = {
                "class_code": class_code,
                "group_code": group_code,
            }
    print(f" ✓  {len(am):,} amateur records")

    # Step 4: Merge and insert
    print("  Building amateur table ...", end="", flush=True)
    rows = []
    for sysid, h in hd.items():
        e = en.get(sysid, {})
        a = am.get(sysid, {})
        class_code = a.get("class_code", "")
        rows.append((
            sysid,
            h.get("call_sign", ""),
            h.get("status", ""),
            h.get("grant_date", ""),
            h.get("expired_date", ""),
            e.get("full_name", ""),
            e.get("first_name", ""),
            e.get("last_name", ""),
            e.get("address", ""),
            e.get("city", ""),
            e.get("state", ""),
            e.get("zip_code", ""),
            e.get("frn", ""),
            OPERATOR_CLASS.get(class_code, class_code),
            class_code,
            a.get("group_code", ""),
        ))

        if len(rows) >= 50000:
            con.executemany(
                "INSERT INTO amateur VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                rows
            )
            con.commit()
            rows = []

    if rows:
        con.executemany(
            "INSERT INTO amateur VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            rows
        )
        con.commit()

    count = con.execute("SELECT COUNT(*) FROM amateur").fetchone()[0]
    print(f" ✓  {count:,} ham licenses loaded")

    con.execute("ANALYZE")
    con.close()

    print(f"\n{'='*55}")
    print(f"  ✓  Done! {count:,} amateur licenses in database")
    print(f"{'='*55}")
    print("\n  Option 10 in search_fcc.py now available!")
    print("  Try looking up your own call sign!!\n")


if __name__ == "__main__":
    main()
