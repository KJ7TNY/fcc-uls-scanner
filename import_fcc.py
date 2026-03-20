#!/usr/bin/env python3
"""
FCC ULS Private Land Mobile - SQLite Importer (Fixed)
======================================================
Imports HD, EN, LO, and FR .dat files into a local SQLite database.
The complete weekly download already contains only current records
so no status filtering is needed.

Usage:
    python3 import_fcc.py

Make sure your .dat files are in ~/fcc-scanner/data/
"""

import sqlite3
import os
import sys

# ---------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------
DAT_FOLDER  = os.path.expanduser("~/fcc-scanner/data")
DB_PATH     = os.path.expanduser("~/fcc-scanner/fcc.db")
# ---------------------------------------------------------------

def connect():
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    return con


def create_tables(con):
    con.executescript("""
        DROP TABLE IF EXISTS hd;
        DROP TABLE IF EXISTS en;
        DROP TABLE IF EXISTS lo;
        DROP TABLE IF EXISTS fr;

        -- License Header (57 columns)
        CREATE TABLE hd (
            record_type             TEXT,
            unique_system_id        TEXT,
            uls_file_number         TEXT,
            ebf_number              TEXT,
            call_sign               TEXT,
            license_status          TEXT,
            radio_service_code      TEXT,
            grant_date              TEXT,
            expired_date            TEXT,
            cancellation_date       TEXT,
            eligibility_rule_num    TEXT,
            eligibility_rule_num2   TEXT,
            alien                   TEXT,
            alien_government        TEXT,
            alien_corporation       TEXT,
            alien_officer           TEXT,
            alien_control           TEXT,
            revoked                 TEXT,
            convicted               TEXT,
            adjudged                TEXT,
            reserved1               TEXT,
            common_carrier          TEXT,
            non_common_carrier      TEXT,
            private_comm            TEXT,
            fixed                   TEXT,
            mobile                  TEXT,
            radiolocation           TEXT,
            satellite               TEXT,
            developmental_sta       TEXT,
            interconnected_service  TEXT,
            certifier_first_name    TEXT,
            certifier_mi            TEXT,
            certifier_last_name     TEXT,
            certifier_suffix        TEXT,
            certifier_title         TEXT,
            female                  TEXT,
            black                   TEXT,
            native_american         TEXT,
            hawaiian                TEXT,
            asian                   TEXT,
            white                   TEXT,
            hispanic                TEXT,
            effective_date          TEXT,
            last_action_date        TEXT,
            auction_id              INTEGER,
            reg_stat_broad_serv     TEXT,
            band_manager            TEXT,
            type_serv_broad_serv    TEXT,
            alien_ruling            TEXT,
            licensee_name_change    TEXT,
            whitespace_ind          TEXT,
            operation_req_auth_stat TEXT,
            operation_req_auth_date TEXT,
            app_waiver_type         TEXT,
            app_waiver_date         TEXT,
            supp_appstatus          TEXT,
            supp_appstatus_date     TEXT
        );

        -- Entity / Licensee (30 columns)
        CREATE TABLE en (
            record_type             TEXT,
            unique_system_id        INTEGER,
            uls_file_number         TEXT,
            ebf_number              TEXT,
            call_sign               TEXT,
            entity_type             TEXT,
            licensee_id             TEXT,
            entity_name             TEXT,
            first_name              TEXT,
            mi                      TEXT,
            last_name               TEXT,
            suffix                  TEXT,
            phone                   TEXT,
            fax                     TEXT,
            email                   TEXT,
            street_address          TEXT,
            city                    TEXT,
            state                   TEXT,
            zip_code                TEXT,
            po_box                  TEXT,
            attention_line          TEXT,
            sgin                    TEXT,
            frn                     TEXT,
            applicant_type_code     TEXT,
            applicant_type_other    TEXT,
            status_code             TEXT,
            status_date             TEXT,
            lic_category_code       TEXT,
            linked_license_id       INTEGER,
            linked_callsign         TEXT
        );

        -- Location / Transmitter Sites (51 columns + 2 computed)
        CREATE TABLE lo (
            record_type             TEXT,
            unique_system_id        INTEGER,
            uls_file_number         TEXT,
            ebf_number              TEXT,
            call_sign               TEXT,
            location_action_perf    TEXT,
            location_type_code      TEXT,
            location_class_code     TEXT,
            location_number         INTEGER,
            site_status             TEXT,
            corresponding_fixed_loc INTEGER,
            location_address        TEXT,
            location_city           TEXT,
            location_county         TEXT,
            location_state          TEXT,
            radius_of_operation     REAL,
            area_of_operation_code  TEXT,
            clearance_ind           TEXT,
            ground_elevation        REAL,
            lat_degrees             INTEGER,
            lat_minutes             INTEGER,
            lat_seconds             REAL,
            lat_direction           TEXT,
            lon_degrees             INTEGER,
            lon_minutes             INTEGER,
            lon_seconds             REAL,
            lon_direction           TEXT,
            max_latency             TEXT,
            nepa                    TEXT,
            quiet_zone_notif_date   TEXT,
            tower_registration_num  TEXT,
            height_support_struct   REAL,
            overall_height_struct   REAL,
            structure_type          TEXT,
            airport_id              TEXT,
            location_name           TEXT,
            units_hand_held         INTEGER,
            units_mobile            INTEGER,
            units_temp_fixed        INTEGER,
            units_aircraft          INTEGER,
            units_itinerant         INTEGER,
            status_code             TEXT,
            status_date             TEXT,
            earth_agree             TEXT,
            col45                   TEXT,
            col46                   TEXT,
            col47                   TEXT,
            col48                   TEXT,
            col49                   TEXT,
            col50                   TEXT,
            col51                   TEXT,
            -- Computed decimal lat/lon (filled in after import)
            latitude                REAL,
            longitude               REAL
        );

        -- Frequency (30 columns)
        CREATE TABLE fr (
            record_type             TEXT,
            unique_system_id        INTEGER,
            uls_file_number         TEXT,
            ebf_number              TEXT,
            call_sign               TEXT,
            location_number         INTEGER,
            antenna_number          INTEGER,
            class_station_code      TEXT,
            op_altitude_code        TEXT,
            frequency               REAL,
            frequency_assigned      REAL,
            frequency_upper_band    REAL,
            frequency_offset        TEXT,
            frequency_channel_block TEXT,
            station_class           TEXT,
            op_altitude_add_info    TEXT,
            power_erp               REAL,
            power_erp_add_info      TEXT,
            tolerance               REAL,
            frequency_ind           TEXT,
            status_code             TEXT,
            status_date             TEXT,
            eirp                    REAL,
            transmitter_make        TEXT,
            transmitter_model       TEXT,
            auto_tx_power_control   TEXT,
            cnt_mobile_units        INTEGER,
            cnt_mobile_paging       INTEGER,
            col29                   TEXT,
            col30                   TEXT
        );

        -- Indexes for fast searching
        CREATE INDEX idx_hd_callsign  ON hd(call_sign);
        CREATE INDEX idx_en_sysid     ON en(unique_system_id);
        CREATE INDEX idx_en_name      ON en(entity_name);
        CREATE INDEX idx_en_type      ON en(entity_type);
        CREATE INDEX idx_lo_sysid     ON lo(unique_system_id);
        CREATE INDEX idx_lo_state     ON lo(location_state);
        CREATE INDEX idx_lo_county    ON lo(location_county);
        CREATE INDEX idx_lo_latlon    ON lo(latitude, longitude);
        CREATE INDEX idx_fr_sysid     ON fr(unique_system_id);
        CREATE INDEX idx_fr_freq      ON fr(frequency);
    """)
    con.commit()
    print("✓ Tables created")


def import_dat(con, filename, table, col_count):
    """Import a pipe-delimited .dat file into a table."""
    filepath = os.path.join(DAT_FOLDER, filename)
    if not os.path.exists(filepath):
        print(f"  ⚠  {filename} not found — skipping")
        return 0

    print(f"  Loading {filename} ...", end="", flush=True)
    rows = []
    extra = 2 if table == "lo" else 0
    placeholders = ",".join(["?"] * col_count + ["NULL"] * extra)

    with open(filepath, encoding="latin-1", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n\r")
            parts = line.split("|")

            # Pad short rows, trim long rows to expected column count
            if len(parts) < col_count:
                parts += [""] * (col_count - len(parts))
            parts = parts[:col_count]

            rows.append(parts)

            # Batch insert every 50,000 rows
            if len(rows) >= 50000:
                con.executemany(
                    f"INSERT OR IGNORE INTO {table} VALUES ({placeholders})",
                    rows
                )
                con.commit()
                rows = []

    # Insert any remaining rows
    if rows:
        con.executemany(
            f"INSERT OR IGNORE INTO {table} VALUES ({placeholders})",
            rows
        )
        con.commit()

    count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f" ✓  {count:,} records loaded")
    return count


def add_decimal_latlon(con):
    """Convert DMS lat/lon to decimal degrees for radius searching."""
    print("  Computing decimal lat/lon ...", end="", flush=True)
    con.execute("""
        UPDATE lo SET
            latitude = CASE
                WHEN lat_direction = 'S'
                THEN -1.0 * (lat_degrees + lat_minutes/60.0 + lat_seconds/3600.0)
                ELSE        (lat_degrees + lat_minutes/60.0 + lat_seconds/3600.0)
            END,
            longitude = CASE
                WHEN lon_direction = 'W'
                THEN -1.0 * (lon_degrees + lon_minutes/60.0 + lon_seconds/3600.0)
                ELSE        (lon_degrees + lon_minutes/60.0 + lon_seconds/3600.0)
            END
        WHERE lat_degrees IS NOT NULL
          AND lat_degrees != ''
          AND lon_degrees IS NOT NULL
          AND lon_degrees != ''
    """)
    con.commit()
    updated = con.execute(
        "SELECT COUNT(*) FROM lo WHERE latitude IS NOT NULL AND latitude != 0"
    ).fetchone()[0]
    print(f" ✓  {updated:,} locations geocoded")


def main():
    os.makedirs(DAT_FOLDER, exist_ok=True)

    # Check that dat files exist
    needed = ["HD.dat", "EN.dat", "LO.dat", "FR.dat"]
    missing = [f for f in needed if not os.path.exists(os.path.join(DAT_FOLDER, f))]
    if missing:
        print(f"\n⚠  Missing files in {DAT_FOLDER}:")
        for f in missing:
            print(f"   - {f}")
        print("\nMake sure you unzipped a_LMpriv.zip into that folder.\n")
        sys.exit(1)

    # Delete old database if it exists so we start fresh
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("  (Removed old fcc.db — starting fresh)")

    print(f"\n{'='*55}")
    print("  FCC ULS Private Land Mobile → SQLite Importer")
    print(f"{'='*55}")
    print(f"  Source : {DAT_FOLDER}")
    print(f"  Output : {DB_PATH}")
    print(f"{'='*55}\n")

    con = connect()
    create_tables(con)

    print("\nImporting files...")

    # Column counts confirmed from actual data
    import_dat(con, "HD.dat", "hd", 57)   # 57 cols
    import_dat(con, "EN.dat", "en", 30)   # 30 cols
    import_dat(con, "LO.dat", "lo", 51)   # 51 cols (+ 2 computed = 53 in table)
    import_dat(con, "FR.dat", "fr", 30)   # 30 cols

    print("\nPost-processing...")
    add_decimal_latlon(con)

    con.execute("ANALYZE")
    con.close()

    db_size = os.path.getsize(DB_PATH) / (1024 * 1024)
    print(f"\n{'='*55}")
    print(f"  ✓  All done!  Database: {db_size:.1f} MB")
    print(f"  Saved to: {DB_PATH}")
    print(f"{'='*55}")
    print("\nNext step: run search_fcc.py to search for transmitters!\n")


if __name__ == "__main__":
    main()
