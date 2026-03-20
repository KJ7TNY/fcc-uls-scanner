#!/usr/bin/env python3
"""
Add US Cities table to FCC database.
Loads uscities.csv from SimpleMaps into fcc.db for offline city lookup.

Usage:
    python3 add_cities.py
"""

import sqlite3
import csv
import os

DB_PATH    = os.path.expanduser("~/fcc-scanner/fcc.db")
CSV_PATH   = os.path.expanduser("~/fcc-scanner/uscities.csv")

def main():
    if not os.path.exists(DB_PATH):
        print("⚠  Database not found! Run import_fcc.py first.")
        return

    if not os.path.exists(CSV_PATH):
        print(f"⚠  uscities.csv not found at {CSV_PATH}")
        print("   Download from https://simplemaps.com/data/us-cities")
        return

    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")

    print("\n  Adding US Cities table...")

    con.executescript("""
        DROP TABLE IF EXISTS cities;
        CREATE TABLE cities (
            city        TEXT,
            city_ascii  TEXT,
            state_id    TEXT,
            state_name  TEXT,
            county_name TEXT,
            lat         REAL,
            lng         REAL,
            population  INTEGER,
            ranking     INTEGER
        );
        CREATE INDEX idx_cities_lookup ON cities(UPPER(city_ascii), UPPER(state_id));
        CREATE INDEX idx_cities_state  ON cities(UPPER(state_id));
    """)
    con.commit()
    print("  ✓ Cities table created")

    print("  Loading uscities.csv ...", end="", flush=True)
    rows = []
    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                rows.append((
                    row['city'],
                    row['city_ascii'],
                    row['state_id'],
                    row['state_name'],
                    row['county_name'],
                    float(row['lat'])  if row['lat']  else None,
                    float(row['lng'])  if row['lng']  else None,
                    int(row['population'].split('.')[0]) if row['population'] else 0,
                    int(row['ranking']) if row['ranking'] else 9,
                ))
            except Exception:
                continue

    con.executemany(
        "INSERT INTO cities VALUES (?,?,?,?,?,?,?,?,?)",
        rows
    )
    con.commit()

    count = con.execute("SELECT COUNT(*) FROM cities").fetchone()[0]
    print(f" ✓  {count:,} cities loaded")

    # Quick test
    test = con.execute("""
        SELECT city, state_id, county_name, lat, lng
        FROM cities
        WHERE UPPER(city_ascii) = 'LEWISTON'
          AND UPPER(state_id) = 'ID'
        LIMIT 3
    """).fetchall()

    print("\n  Test lookup — Lewiston ID:")
    for r in test:
        print(f"    {r[0]}, {r[1]} ({r[2]}) → {r[3]}, {r[4]}")

    con.execute("ANALYZE")
    con.close()
    print("\n  ✓  Done! City lookup is now available in search_fcc.py!\n")

if __name__ == "__main__":
    main()
