#!/usr/bin/env python3
"""
FCC ULS Transmitter Search - Final Version
==========================================
Search your local FCC database by:
  1. State + County
  2. Radius search by coordinates
  3. Call sign lookup
  4. Company / licensee name search
  5. Radius search by city name (offline!)
  6. Frequency range search (find who's on a band!)
  7. Exit

Usage:
    python3 search_fcc.py
"""

import sqlite3
import os
import math
from datetime import datetime
from collections import defaultdict

DB_PATH = os.path.expanduser("~/fcc-scanner/fcc.db")
REF_DB  = os.path.expanduser("~/fcc-scanner/fcc_reference.db")

# Emission designator decoder
EMISSION_TYPES = {
    "F3E": "FM Analog Voice",
    "F2D": "FM Digital Data",
    "F1E": "FM Digital Voice",
    "F1D": "FM Digital Data",
    "F7E": "FM Digital Voice",
    "F7W": "FM Digital Voice",
    "G3E": "Phase Mod Analog",
    "G7E": "Phase Mod Digital",
    "G7W": "Phase Mod Digital",
    "D7E": "Digital Voice",
    "D7W": "Digital Voice",
    "P0N": "Pulsed/Radar",
    "F3F": "FM Analog Video",
    "F9W": "FM Mixed Digital",
    "W7E": "Digital Mixed",
    "F8E": "FM Digital Mixed",
    "FXE": "Digital (NXDN/P25)",
    "FXD": "Digital Data",
}

def decode_emission(em, con=None):
    if not em:
        return ""
    # Try full designator lookup in reference db first
    if con:
        desc = lookup_emission(con, em)
        if desc:
            return f" ({desc})"
    # Fall back to suffix lookup in hardcoded dict
    if len(em) >= 3:
        suffix = em[-3:].upper()
        label = EMISSION_TYPES.get(suffix, "")
        return f" ({label})" if label else ""
    return ""


def haversine(lat1, lon1, lat2, lon2):
    R = 3958.8
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def connect():
    if not os.path.exists(DB_PATH):
        print(f"\n⚠  Database not found at {DB_PATH}")
        print("   Please run import_fcc.py first!\n")
        exit(1)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    # Attach reference database if available
    if os.path.exists(REF_DB):
        con.execute(f"ATTACH DATABASE '{REF_DB}' AS ref")
    return con


def lookup_emission(con, designator):
    """Look up emission designator description from reference db."""
    if not designator or not os.path.exists(REF_DB):
        return None
    try:
        r = con.execute(
            "SELECT description FROM ref.emission_lookup WHERE designator = ?",
            (designator.strip(),)
        ).fetchone()
        return r[0] if r else None
    except Exception:
        return None


def lookup_station_class(con, code):
    """Look up station class description from reference db."""
    if not code or not os.path.exists(REF_DB):
        return None
    try:
        r = con.execute(
            "SELECT name, description FROM ref.station_class WHERE code = ?",
            (code.strip(),)
        ).fetchone()
        return f"{r[0]} — {r[1]}" if r else None
    except Exception:
        return None


def get_frequencies(con, unique_system_id, location_number=None):
    """Get deduplicated frequency info for a transmitter site."""
    has_em = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='em'"
    ).fetchone() is not None

    if has_em:
        rows = con.execute("""
            SELECT DISTINCT
                fr.frequency,
                fr.station_class,
                fr.power_erp,
                em.emission_designator
            FROM fr
            LEFT JOIN em ON fr.unique_system_id = em.unique_system_id
                AND ABS(fr.frequency - em.frequency) < 0.01
                AND em.emission_designator != ''
            WHERE fr.unique_system_id = ?
              AND (? IS NULL OR CAST(fr.antenna_number AS TEXT) = CAST(? AS TEXT))
              AND fr.frequency IS NOT NULL
              AND fr.frequency != ''
            ORDER BY fr.frequency, fr.station_class, em.emission_designator
        """, (str(unique_system_id), str(location_number) if location_number else None, str(location_number) if location_number else None)).fetchall()
        # Fall back to all frequencies if location filter returns nothing
        if not rows:
            rows = con.execute("""
                SELECT DISTINCT
                    fr.frequency,
                    fr.station_class,
                    fr.power_erp,
                    em.emission_designator
                FROM fr
                LEFT JOIN em ON fr.unique_system_id = em.unique_system_id
                    AND ABS(fr.frequency - em.frequency) < 0.01
                    AND em.emission_designator != ''
                WHERE fr.unique_system_id = ?
                  AND fr.frequency IS NOT NULL
                  AND fr.frequency != ''
                ORDER BY fr.frequency, fr.station_class, em.emission_designator
            """, (str(unique_system_id),)).fetchall()
    else:
        rows = con.execute("""
            SELECT DISTINCT
                fr.frequency,
                fr.station_class,
                fr.power_erp,
                NULL as emission_designator
            FROM fr
            WHERE fr.unique_system_id = ?
              AND (? IS NULL OR CAST(fr.antenna_number AS TEXT) = CAST(? AS TEXT))
              AND fr.frequency IS NOT NULL
              AND fr.frequency != ''
            ORDER BY fr.frequency, fr.station_class
        """, (str(unique_system_id), str(location_number) if location_number else None, str(location_number) if location_number else None)).fetchall()
        if not rows:
            rows = con.execute("""
                SELECT DISTINCT
                    fr.frequency,
                    fr.station_class,
                    fr.power_erp,
                    NULL as emission_designator
                FROM fr
                WHERE fr.unique_system_id = ?
                  AND fr.frequency IS NOT NULL
                  AND fr.frequency != ''
                ORDER BY fr.frequency, fr.station_class
            """, (str(unique_system_id),)).fetchall()

    # Deduplicate: same freq+class+emission = one row
    seen = set()
    deduped = []
    for r in rows:
        key = (round(float(r['frequency']), 4) if r['frequency'] else 0,
               r['station_class'] or '',
               r['emission_designator'] or '')
        if key not in seen:
            seen.add(key)
            deduped.append(r)
    return deduped


def format_freq_lines(freq_rows, con=None):
    if not freq_rows:
        return ["    (none on file)"]
    lines = []
    for r in freq_rows:
        freq   = r['frequency']
        sclass = r['station_class'] or '??'
        power  = r['power_erp']
        em     = r['emission_designator'] or ''
        if not freq:
            continue
        power_str = f"{power:.1f}W" if power else "?W"
        em_str    = f"{em}{decode_emission(em, con)}" if em else "N/A"
        lines.append(f"    {float(freq):>12.5f} MHz | {sclass:<4s} | {power_str:<8s} | {em_str}")
    return lines if lines else ["    (none on file)"]


def print_single_result(r, freq_rows, distance=None):
    print(f"\n  Call Sign : {r['call_sign'] or 'N/A'}")
    print(f"  Licensee  : {r['entity_name'] or 'N/A'}")
    if r['frn']:
        print(f"  FRN       : {r['frn']}")
    city = r['location_city'] or ''
    state = r['location_state'] or ''
    if city or state:
        print(f"  Location  : {city}{', ' + state if state else ''}")
    county = r['location_county'] or ''
    if county:
        print(f"  County    : {county}")
    if r['latitude'] and r['longitude']:
        print(f"  Coords    : {r['latitude']:.6f}, {r['longitude']:.6f}")
    if r['location_name'] and r['location_name'] not in ('N', ''):
        print(f"  Site Name : {r['location_name']}")
    if distance is not None:
        print(f"  Distance  : {distance:.1f} miles")
    print(f"  {'─'*62}")
    print(f"    {'Frequency':>12s} MHz   {'Class':<4s}   {'Power':<8s}   Emission")
    print(f"  {'─'*62}")
    for line in freq_rows:
        print(line)
    print(f"  {'─'*62}")


def print_results(con, rows, title, distances=None):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"  {len(rows)} transmitter site(s) found")
    print(f"{'='*70}")
    if not rows:
        print("  No results found.")
        return
    for i, r in enumerate(rows):
        dist = distances[i] if distances else None
        freq_rows = get_frequencies(con, r['unique_system_id'], r['location_number'])
        print_single_result(r, format_freq_lines(freq_rows, con), distance=dist)


def save_results(con, rows, filename, distances=None):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base, ext = os.path.splitext(filename)
    filename = f"{base}_{ts}{ext}"
    reports_dir = os.path.expanduser("~/fcc-scanner/reports")
    os.makedirs(reports_dir, exist_ok=True)
    outpath = os.path.join(reports_dir, filename)
    with open(outpath, "w") as f:
        f.write(f"FCC Transmitter Search Results\n")
        f.write(f"{'='*62}\n\n")
        for i, r in enumerate(rows):
            dist = distances[i] if distances else None
            freq_rows = get_frequencies(con, r['unique_system_id'], r['location_number'])
            f.write(f"Call Sign : {r['call_sign'] or 'N/A'}\n")
            f.write(f"Licensee  : {r['entity_name'] or 'N/A'}\n")
            if r['frn']:
                f.write(f"FRN       : {r['frn']}\n")
            city = r['location_city'] or ''
            state = r['location_state'] or ''
            if city or state:
                f.write(f"Location  : {city}{', ' + state if state else ''}\n")
            if r['location_county']:
                f.write(f"County    : {r['location_county']}\n")
            if r['latitude'] and r['longitude']:
                f.write(f"Coords    : {r['latitude']:.6f}, {r['longitude']:.6f}\n")
            if dist is not None:
                f.write(f"Distance  : {dist:.1f} miles\n")
            f.write(f"{'─'*62}\n")
            f.write(f"    {'Frequency':>12s} MHz   {'Class':<4s}   {'Power':<8s}   Emission\n")
            f.write(f"{'─'*62}\n")
            for line in format_freq_lines(freq_rows, con):
                f.write(line + "\n")
            f.write(f"{'─'*62}\n\n")
    print(f"  ✓  Saved to {outpath}")


def base_query():
    return """
        SELECT
            lo.unique_system_id,
            lo.location_number,
            COALESCE(NULLIF(lo.call_sign,''),
                (SELECT NULLIF(call_sign,'') FROM hd
                 WHERE hd.unique_system_id = lo.unique_system_id LIMIT 1)
            ) AS call_sign,
            COALESCE(
                (SELECT entity_name FROM en
                 WHERE en.unique_system_id = lo.unique_system_id
                   AND en.entity_type = 'L' LIMIT 1),
                (SELECT entity_name FROM en
                 WHERE en.unique_system_id = lo.unique_system_id
                 LIMIT 1)
            ) AS entity_name,
            COALESCE(
                (SELECT frn FROM en
                 WHERE en.unique_system_id = lo.unique_system_id
                   AND en.entity_type = 'L'
                   AND en.frn IS NOT NULL AND en.frn != ''
                 LIMIT 1),
                (SELECT frn FROM en
                 WHERE en.unique_system_id = lo.unique_system_id
                   AND en.frn IS NOT NULL AND en.frn != ''
                 LIMIT 1)
            ) AS frn,
            lo.location_city,
            lo.location_state,
            lo.location_county,
            lo.location_name,
            lo.latitude,
            lo.longitude
        FROM lo
    """


def do_radius_search(con, lat, lon, radius, freq_low=None, freq_high=None):
    """Core radius search used by options 2, 5, and 6."""
    lat_delta = radius / 69.0
    lon_delta = radius / (69.0 * math.cos(math.radians(lat)))

    # If frequency filter, only grab system IDs that have matching frequencies
    freq_filter = ""
    if freq_low is not None and freq_high is not None:
        freq_filter = f"""
            AND lo.unique_system_id IN (
                SELECT unique_system_id FROM fr
                WHERE frequency BETWEEN {freq_low} AND {freq_high}
            )
        """

    candidates = con.execute(
        base_query() + f"""
        WHERE lo.latitude  BETWEEN ? AND ?
          AND lo.longitude BETWEEN ? AND ?
          AND lo.latitude IS NOT NULL
          {freq_filter}
        GROUP BY lo.unique_system_id, lo.location_number
        """,
        (lat - lat_delta, lat + lat_delta,
         lon - lon_delta, lon + lon_delta)
    ).fetchall()

    results = []
    distances = []
    for row in candidates:
        dist = haversine(lat, lon, row['latitude'], row['longitude'])
        if dist <= radius:
            results.append(row)
            distances.append(dist)

    paired = sorted(zip(distances, results), key=lambda x: x[0])
    distances = [p[0] for p in paired]
    results   = [p[1] for p in paired]
    return results, distances


def lookup_city(con, city, state):
    """Look up city coordinates from the offline cities database."""
    has_cities = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='cities'"
    ).fetchone() is not None

    if not has_cities:
        print("  ⚠  Cities database not loaded! Run add_cities.py first.")
        return None, None, None

    matches = con.execute("""
        SELECT city, state_id, county_name, lat, lng
        FROM cities
        WHERE UPPER(city_ascii) LIKE UPPER(?)
          AND UPPER(state_id) = ?
        ORDER BY ranking, population DESC
        LIMIT 5
    """, (f"%{city}%", state.upper())).fetchall()

    if not matches:
        print(f"  ⚠  No city found matching '{city}' in {state.upper()}")
        return None, None, None

    if len(matches) > 1:
        print(f"\n  Found {len(matches)} matches:")
        for i, m in enumerate(matches):
            print(f"  {i+1} - {m[0]}, {m[1]} ({m[2]} County) → {m[3]:.4f}, {m[4]:.4f}")
        try:
            pick = int(input("\n  Enter number to select: ").strip()) - 1
            if pick < 0 or pick >= len(matches):
                print("  ⚠  Invalid selection.")
                return None, None, None
        except ValueError:
            return None, None, None
        chosen = matches[pick]
    else:
        chosen = matches[0]

    print(f"\n  ✓ Using: {chosen[0]}, {chosen[1]} ({chosen[2]} County)")
    print(f"    Center: {chosen[3]:.4f}, {chosen[4]:.4f}")
    return chosen[3], chosen[4], chosen[0]


# ─────────────────────────────────────────────
#  SEARCH FUNCTIONS
# ─────────────────────────────────────────────

def search_by_county(con):
    print("\n--- Search by State + County ---")
    state  = input("  Enter 2-letter state code (e.g. WA, CA, TX): ").strip().upper()
    county = input("  Enter county name (partial ok, e.g. 'Asotin'): ").strip()
    county_clean = county.replace("County","").replace("county","").strip()

    rows = con.execute(
        base_query() + """
        WHERE lo.location_state = ?
          AND UPPER(lo.location_county) LIKE UPPER(?)
          AND lo.latitude IS NOT NULL
        GROUP BY lo.unique_system_id, lo.location_number
        ORDER BY entity_name
        """,
        (state, f"%{county_clean}%")
    ).fetchall()

    print_results(con, rows, f"Transmitters in {county_clean} County, {state}")
    if rows:
        save = input("\n  Save to file? (y/n): ").strip().lower()
        if save == 'y':
            save_results(con, rows, f"results_{state}_{county_clean}.txt")


def search_by_radius(con):
    print("\n--- Radius Search by Coordinates ---")
    print("  Tip: Right-click any spot in Google Maps to copy coordinates.\n")
    try:
        lat    = float(input("  Center Latitude  (e.g. 46.3365): ").strip())
        lon    = float(input("  Center Longitude (e.g. -117.0551): ").strip())
        radius = float(input("  Search radius in miles (e.g. 10): ").strip())
    except ValueError:
        print("  ⚠  Invalid number.")
        return

    results, distances = do_radius_search(con, lat, lon, radius)
    print_results(con, results,
                  f"Transmitters within {radius} miles of {lat:.4f}, {lon:.4f}",
                  distances)
    if results:
        save = input("\n  Save to file? (y/n): ").strip().lower()
        if save == 'y':
            save_results(con, results, f"results_radius_{radius}mi.txt", distances)


def search_by_callsign(con):
    print("\n--- Call Sign Lookup ---")
    call = input("  Enter call sign (e.g. WQZX123): ").strip().upper()

    rows = con.execute(
        base_query() + """
        WHERE lo.unique_system_id IN (
            SELECT unique_system_id FROM hd WHERE call_sign = ?
        )
        GROUP BY lo.unique_system_id, lo.location_number
        ORDER BY lo.location_state, lo.location_city
        """,
        (call,)
    ).fetchall()

    print_results(con, rows, f"All transmitter sites for {call}")
    if rows:
        save = input("\n  Save to file? (y/n): ").strip().lower()
        if save == 'y':
            save_results(con, rows, f"results_callsign_{call}.txt")


def search_by_name(con):
    print("\n--- Company / Licensee Name Search ---")
    name = input("  Enter company name (partial ok, e.g. 'Walmart'): ").strip()

    rows = con.execute(
        base_query() + """
        WHERE lo.unique_system_id IN (
            SELECT unique_system_id FROM en
            WHERE UPPER(entity_name) LIKE UPPER(?)
        )
          AND lo.latitude IS NOT NULL
        GROUP BY lo.unique_system_id, lo.location_number
        ORDER BY lo.location_state, lo.location_city
        """,
        (f"%{name}%",)
    ).fetchall()

    print_results(con, rows, f"Transmitter sites matching '{name}'")
    if rows:
        save = input("\n  Save to file? (y/n): ").strip().lower()
        if save == 'y':
            save_results(con, rows, f"results_name_{name}.txt")


def search_by_city(con):
    print("\n--- Radius Search by City Name ---")
    print("  Offline city lookup — no internet needed!\n")

    city   = input("  Enter city name (e.g. Lewiston): ").strip()
    state  = input("  Enter 2-letter state code (e.g. ID): ").strip().upper()

    lat, lon, city_name = lookup_city(con, city, state)
    if lat is None:
        return

    try:
        radius = float(input("  Search radius in miles (e.g. 10): ").strip())
    except ValueError:
        print("  ⚠  Invalid number.")
        return

    results, distances = do_radius_search(con, lat, lon, radius)
    print_results(con, results,
                  f"Transmitters within {radius} miles of {city_name}, {state}",
                  distances)
    if results:
        save = input("\n  Save to file? (y/n): ").strip().lower()
        if save == 'y':
            save_results(con, results,
                         f"results_{city_name}_{state}_{radius}mi.txt", distances)


def search_by_frequency_range(con):
    print("\n--- Frequency Range Search ---")
    print("  Find every transmitter on a specific band in your area.\n")
    print("  Common ranges:")
    print("    VHF Low  :  30 -  50 MHz  (old fire/police)")
    print("    VHF High : 150 - 174 MHz  (fire, EMS, business)")
    print("    UHF      : 450 - 470 MHz  (business, GMRS)")
    print("    800 MHz  : 806 - 869 MHz  (trunked systems)")
    print()

    try:
        freq_low  = float(input("  Low frequency  (MHz, e.g. 150): ").strip())
        freq_high = float(input("  High frequency (MHz, e.g. 174): ").strip())
    except ValueError:
        print("  ⚠  Invalid frequency.")
        return

    if freq_low >= freq_high:
        print("  ⚠  Low frequency must be less than high frequency.")
        return

    print()
    print("  Search area:")
    print("  1 - By city name")
    print("  2 - By coordinates")
    print("  3 - By state + county")
    area = input("\n  Enter choice (1-3): ").strip()

    if area == "1":
        city  = input("  City name: ").strip()
        state = input("  State code: ").strip().upper()
        lat, lon, city_name = lookup_city(con, city, state)
        if lat is None:
            return
        try:
            radius = float(input("  Radius in miles: ").strip())
        except ValueError:
            print("  ⚠  Invalid number.")
            return
        results, distances = do_radius_search(con, lat, lon, radius, freq_low, freq_high)
        title = f"{freq_low}-{freq_high} MHz within {radius} miles of {city_name}, {state}"
        print_results(con, results, title, distances)
        if results:
            save = input("\n  Save to file? (y/n): ").strip().lower()
            if save == 'y':
                save_results(con, results,
                             f"results_freq_{freq_low}-{freq_high}_{city_name}.txt",
                             distances)

    elif area == "2":
        try:
            lat    = float(input("  Latitude: ").strip())
            lon    = float(input("  Longitude: ").strip())
            radius = float(input("  Radius in miles: ").strip())
        except ValueError:
            print("  ⚠  Invalid number.")
            return
        results, distances = do_radius_search(con, lat, lon, radius, freq_low, freq_high)
        title = f"{freq_low}-{freq_high} MHz within {radius} miles of {lat:.4f}, {lon:.4f}"
        print_results(con, results, title, distances)
        if results:
            save = input("\n  Save to file? (y/n): ").strip().lower()
            if save == 'y':
                save_results(con, results,
                             f"results_freq_{freq_low}-{freq_high}_radius.txt",
                             distances)

    elif area == "3":
        state  = input("  State code: ").strip().upper()
        county = input("  County name: ").strip()
        county_clean = county.replace("County","").replace("county","").strip()

        rows = con.execute(
            base_query() + """
            WHERE lo.location_state = ?
              AND UPPER(lo.location_county) LIKE UPPER(?)
              AND lo.latitude IS NOT NULL
              AND lo.unique_system_id IN (
                  SELECT unique_system_id FROM fr
                  WHERE frequency BETWEEN ? AND ?
              )
            GROUP BY lo.unique_system_id, lo.location_number
            ORDER BY entity_name
            """,
            (state, f"%{county_clean}%", freq_low, freq_high)
        ).fetchall()

        title = f"{freq_low}-{freq_high} MHz in {county_clean} County, {state}"
        print_results(con, rows, title)
        if rows:
            save = input("\n  Save to file? (y/n): ").strip().lower()
            if save == 'y':
                save_results(con, rows,
                             f"results_freq_{freq_low}-{freq_high}_{state}_{county_clean}.txt")
    else:
        print("  ⚠  Invalid choice.")


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────




def search_repeaters(con):
    print("\n--- Repeater Finder ---")
    print("  Shows licenses with BOTH FB2 outputs and FX1 inputs")
    print("  Groups all outputs and inputs per license\n")

    print("  Search area:")
    print("  1 - By city name")
    print("  2 - By coordinates")
    print("  3 - By state + county")
    print("  4 - By frequency range + city")
    area = input("\n  Enter choice (1-4): ").strip()

    freq_low  = None
    freq_high = None
    lat       = None
    lon       = None
    radius    = None
    state     = None
    county    = None
    label     = ""

    if area == "1":
        city  = input("  City name: ").strip()
        state = input("  State code: ").strip().upper()
        lat, lon, city_name = lookup_city(con, city, state)
        if lat is None:
            return
        try:
            radius = float(input("  Radius in miles: ").strip())
        except ValueError:
            print("  ⚠  Invalid number.")
            return
        label = f"{city_name}, {state} within {radius} miles"

    elif area == "2":
        try:
            lat    = float(input("  Latitude: ").strip())
            lon    = float(input("  Longitude: ").strip())
            radius = float(input("  Radius in miles: ").strip())
        except ValueError:
            print("  ⚠  Invalid number.")
            return
        label = f"{lat:.4f}, {lon:.4f} within {radius} miles"

    elif area == "3":
        state  = input("  State code: ").strip().upper()
        county = input("  County name: ").strip()
        county = county.replace("County","").replace("county","").strip()
        label  = f"{county} County, {state}"

    elif area == "4":
        city  = input("  City name: ").strip()
        state = input("  State code: ").strip().upper()
        lat, lon, city_name = lookup_city(con, city, state)
        if lat is None:
            return
        try:
            radius    = float(input("  Radius in miles: ").strip())
            freq_low  = float(input("  Low frequency  (MHz): ").strip())
            freq_high = float(input("  High frequency (MHz): ").strip())
        except ValueError:
            print("  ⚠  Invalid number.")
            return
        label = f"{freq_low}-{freq_high} MHz repeaters near {city_name}, {state} within {radius} miles"
    else:
        print("  ⚠  Invalid choice.")
        return

    print(f"\n  Searching for repeater systems...\n")

    fr_freq_filter = ""
    if freq_low and freq_high:
        fr_freq_filter = f"AND frequency BETWEEN {freq_low} AND {freq_high}"

    # Get system IDs that have BOTH FB2 and FX1 in the search area
    if lat is not None and radius is not None:
        lat_delta = radius / 69.0
        lon_delta = radius / (69.0 * math.cos(math.radians(lat)))
        sysids = con.execute(f"""
            SELECT DISTINCT unique_system_id FROM lo
            WHERE latitude  BETWEEN {lat - lat_delta} AND {lat + lat_delta}
              AND longitude BETWEEN {lon - lon_delta} AND {lon + lon_delta}
              AND latitude IS NOT NULL
              AND unique_system_id IN (
                  SELECT unique_system_id FROM fr
                  WHERE station_class = 'FB2'
                  {fr_freq_filter}
              )
              AND unique_system_id IN (
                  SELECT unique_system_id FROM fr
                  WHERE station_class = 'FX1'
              )
        """).fetchall()
    elif state and county:
        sysids = con.execute(f"""
            SELECT DISTINCT unique_system_id FROM lo
            WHERE UPPER(location_state) = UPPER('{state}')
              AND UPPER(location_county) LIKE UPPER('%{county}%')
              AND unique_system_id IN (
                  SELECT unique_system_id FROM fr
                  WHERE station_class = 'FB2'
                  {fr_freq_filter}
              )
              AND unique_system_id IN (
                  SELECT unique_system_id FROM fr
                  WHERE station_class = 'FX1'
              )
        """).fetchall()
    else:
        print("  ⚠  No valid search area.")
        return

    if not sysids:
        print("  No repeater systems found in this area.")
        return

    results = []

    for (sysid,) in sysids:
        # Get entity name
        entity = con.execute("""
            SELECT COALESCE(
                (SELECT entity_name FROM en
                 WHERE unique_system_id = ? AND entity_type = 'L' LIMIT 1),
                (SELECT entity_name FROM en
                 WHERE unique_system_id = ? LIMIT 1)
            )
        """, (sysid, sysid)).fetchone()
        entity_name = entity[0] if entity and entity[0] else "N/A"

        # Get call sign
        cs = con.execute("""
            SELECT NULLIF(call_sign,'') FROM hd
            WHERE unique_system_id = ? LIMIT 1
        """, (sysid,)).fetchone()
        call_sign = cs[0] if cs and cs[0] else "N/A"

        # Get all unique FB2 output frequencies with emission
        fb2_rows = con.execute("""
            SELECT DISTINCT fr.frequency, fr.power_erp, em.emission_designator
            FROM fr
            LEFT JOIN em ON fr.unique_system_id = em.unique_system_id
                AND ABS(fr.frequency - em.frequency) < 0.01
                AND em.emission_designator != ''
            WHERE fr.unique_system_id = ?
              AND fr.station_class = 'FB2'
              AND fr.frequency IS NOT NULL AND fr.frequency != ''
            ORDER BY fr.frequency
        """, (sysid,)).fetchall()

        # Get all unique FX1 input frequencies with emission
        fx1_rows = con.execute("""
            SELECT DISTINCT fr.frequency, fr.power_erp, em.emission_designator
            FROM fr
            LEFT JOIN em ON fr.unique_system_id = em.unique_system_id
                AND ABS(fr.frequency - em.frequency) < 0.01
                AND em.emission_designator != ''
            WHERE fr.unique_system_id = ?
              AND fr.station_class = 'FX1'
              AND fr.frequency IS NOT NULL AND fr.frequency != ''
            ORDER BY fr.frequency
        """, (sysid,)).fetchall()

        # Deduplicate by frequency
        seen = set()
        fb2_deduped = []
        for r in fb2_rows:
            if round(float(r[0]),4) not in seen:
                seen.add(round(float(r[0]),4))
                fb2_deduped.append(r)

        seen = set()
        fx1_deduped = []
        for r in fx1_rows:
            if round(float(r[0]),4) not in seen:
                seen.add(round(float(r[0]),4))
                fx1_deduped.append(r)

        if not fb2_deduped or not fx1_deduped:
            continue

        # Calculate offsets between paired outputs and inputs (top to top)
        # If same number of outputs and inputs, pair them top-to-bottom
        # Otherwise calculate all unique offsets
        raw_offsets = []
        if len(fb2_deduped) == len(fx1_deduped):
            # Pair top to top
            for out_r, in_r in zip(fb2_deduped, fx1_deduped):
                off = round(float(in_r[0]) - float(out_r[0]), 4)
                raw_offsets.append(off)
        else:
            # Different counts - get unique offset values
            seen_off = set()
            for out_r in fb2_deduped:
                for in_r in fx1_deduped:
                    off = round(float(in_r[0]) - float(out_r[0]), 4)
                    off_key = round(abs(off), 3)
                    if off_key not in seen_off:
                        seen_off.add(off_key)
                        raw_offsets.append(off)

        def label_offset(off):
            off_str = f"+{off:.4f}" if off > 0 else f"{off:.4f}"
            abs_off = abs(off)
            if abs(abs_off - 5.0) < 0.01:
                off_str += " ★ Standard UHF"
            elif abs(abs_off - 9.0) < 0.01:
                off_str += " ★ Gov UHF"
            elif abs(abs_off - 45.0) < 0.5:
                off_str += " ★ 800 MHz"
            elif abs(abs_off - 30.0) < 0.5:
                off_str += " ★ 700 MHz"
            elif abs(abs_off - 0.6) < 0.02:
                off_str += " ★ Ham VHF"
            return off_str

        # Smart offset display — if all offsets are the same show once
        unique_offsets = list(set(round(o, 3) for o in raw_offsets))
        if len(unique_offsets) == 1:
            count = len(raw_offsets)
            count_str = f"  (same across all {count} pairs)" if count > 1 else ""
            offsets = [label_offset(raw_offsets[0]) + count_str + " MHz"]
        else:
            offsets = [label_offset(o) + " MHz" for o in raw_offsets]

        # Get best location
        loc = con.execute("""
            SELECT location_city, location_state, location_county,
                   latitude, longitude
            FROM lo WHERE unique_system_id = ?
            AND latitude IS NOT NULL AND latitude != 0
            LIMIT 1
        """, (sysid,)).fetchone()

        if not loc:
            continue

        distance = None
        if lat is not None and loc[3]:
            distance = haversine(lat, lon, loc[3], loc[4])
            if distance > radius:
                continue

        results.append({
            'entity_name': entity_name,
            'call_sign':   call_sign,
            'city':        loc[0] or '',
            'state':       loc[1] or '',
            'county':      loc[2] or '',
            'lat':         loc[3],
            'lon':         loc[4],
            'distance':    distance,
            'fb2':         fb2_deduped,
            'fx1':         fx1_deduped,
            'offsets':     offsets,
        })

    # Sort by distance
    if lat is not None:
        results.sort(key=lambda x: x['distance'] if x['distance'] else 999)

    print(f"\n{'='*70}")
    print(f"  Confirmed Repeater Systems — {label}")
    print(f"  {len(results)} repeater system(s) found")
    print(f"{'='*70}")

    output_lines = []
    output_lines.append(f"FCC Repeater Search Results\n")
    output_lines.append(f"Search: {label}\n")
    output_lines.append(f"{'='*70}\n\n")

    for r in results:
        loc_str  = f"{r['city']}, {r['state']}" if r['city'] else r['state']
        dist_str = f"  —  {r['distance']:.1f} miles" if r['distance'] is not None else ""

        print(f"\n  {'━'*62}")
        print(f"  {r['entity_name']}")
        print(f"  Call Sign : {r['call_sign']}   {loc_str}{dist_str}")
        if r['county']:
            print(f"  County    : {r['county']}")
        if r['lat'] and r['lon']:
            print(f"  Coords    : {r['lat']:.6f}, {r['lon']:.6f}")

        output_lines.append(f"{'━'*62}\n")
        output_lines.append(f"{r['entity_name']}\n")
        output_lines.append(f"Call Sign : {r['call_sign']}   {loc_str}{dist_str}\n")
        if r['county']:
            output_lines.append(f"County    : {r['county']}\n")
        if r['lat'] and r['lon']:
            output_lines.append(f"Coords    : {r['lat']:.6f}, {r['lon']:.6f}\n")

        # Show outputs
        print(f"  {'─'*62}")
        print(f"  OUTPUTS (FB2 — what you hear on scanner):")
        output_lines.append(f"{'─'*62}\n")
        output_lines.append(f"OUTPUTS (FB2 — what you hear on scanner):\n")
        for row in r['fb2']:
            pwr = f"{row[1]:.1f}W" if row[1] else "?W"
            em  = f"  {row[2]}{decode_emission(row[2])}" if row[2] else ""
            line = f"    ▶  {float(row[0]):>12.5f} MHz  {pwr:<8}{em}"
            print(line)
            output_lines.append(line.strip() + "\n")

        # Show inputs
        print(f"  {'─'*62}")
        print(f"  INPUTS  (FX1 — what radios transmit into repeater):")
        output_lines.append(f"{'─'*62}\n")
        output_lines.append(f"INPUTS  (FX1 — what radios transmit into repeater):\n")
        for row in r['fx1']:
            pwr = f"{row[1]:.1f}W" if row[1] else "?W"
            em  = f"  {row[2]}{decode_emission(row[2])}" if row[2] else ""
            line = f"    ▷  {float(row[0]):>12.5f} MHz  {pwr:<8}{em}"
            print(line)
            output_lines.append(line.strip() + "\n")

        # Show offsets
        print(f"  {'─'*62}")
        print(f"  OFFSET(S):")
        output_lines.append(f"{'─'*62}\n")
        output_lines.append(f"OFFSET(S):\n")
        for off in r['offsets']:
            print(f"    {off} MHz")
            output_lines.append(f"  {off} MHz\n")

        output_lines.append("\n")

    print(f"\n  {'═'*62}")

    if results:
        save = input("\n  Save to file? (y/n): ").strip().lower()
        if save == 'y':
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_label = label.replace(" ","_").replace(",","").replace("/","-")[:50]
            reports_dir = os.path.expanduser("~/fcc-scanner/reports")
            os.makedirs(reports_dir, exist_ok=True)
            outpath = os.path.join(reports_dir, f"repeaters_{safe_label}_{ts}.txt")
            with open(outpath, "w") as f:
                f.writelines(output_lines)
            print(f"  ✓  Saved to {outpath}")




def search_reference(con):
    print("\n--- Reference Lookup ---")
    print("  Look up any emission designator or station class code\n")
    print("  1 - Emission designator  (e.g. 8K10F1W, 11K2F3E)")
    print("  2 - Station class code   (e.g. FB2, FX1, MO3)")
    print("  3 - Browse all station classes")
    print("  4 - Browse all emission designators")

    choice = input("\n  Enter choice (1-4): ").strip()

    if choice == "1":
        code = input("  Enter emission designator: ").strip().upper()
        r = con.execute(
            "SELECT designator, bandwidth, modulation, info_type, description FROM ref.emission_lookup WHERE designator = ?",
            (code,)
        ).fetchone()
        if r:
            print(f"\n  {'='*60}")
            print(f"  Designator : {r[0]}")
            print(f"  Bandwidth  : {r[1]}")
            print(f"  Modulation : {r[2]}")
            print(f"  Info Type  : {r[3]}")
            print(f"  Description: {r[4]}")
            print(f"  {'='*60}")
        else:
            # Try partial match
            rows = con.execute(
                "SELECT designator, description FROM ref.emission_lookup WHERE designator LIKE ? LIMIT 10",
                (f"%{code}%",)
            ).fetchall()
            if rows:
                print(f"\n  No exact match — similar codes:")
                for row in rows:
                    print(f"    {row[0]:<12} — {row[1]}")
            else:
                print(f"  ⚠  No match found for {code}")
                print(f"  Tip: Use the last 3 characters for type — F3E=FM Analog, F1E=Digital Voice, F1D=Digital Data")

    elif choice == "2":
        code = input("  Enter station class code: ").strip().upper()
        r = con.execute(
            "SELECT code, name, description FROM ref.station_class WHERE code = ?",
            (code,)
        ).fetchone()
        if r:
            print(f"\n  {'='*60}")
            print(f"  Code       : {r[0]}")
            print(f"  Name       : {r[1]}")
            print(f"  Description: {r[2]}")
            print(f"  {'='*60}")
        else:
            rows = con.execute(
                "SELECT code, name, description FROM ref.station_class WHERE code LIKE ? LIMIT 10",
                (f"%{code}%",)
            ).fetchall()
            if rows:
                print(f"\n  No exact match — similar codes:")
                for row in rows:
                    print(f"    {row[0]:<6} {row[1]:<30} — {row[2]}")
            else:
                print(f"  ⚠  No match found for {code}")

    elif choice == "3":
        print(f"\n  {'─'*70}")
        print(f"  {'Code':<8} {'Name':<30} Description")
        print(f"  {'─'*70}")
        rows = con.execute(
            "SELECT code, name, description FROM ref.station_class ORDER BY code"
        ).fetchall()
        for r in rows:
            print(f"  {r[0]:<8} {r[1]:<30} {r[2]}")
        print(f"  {'─'*70}")

    elif choice == "4":
        print(f"\n  {'─'*70}")
        print(f"  {'Designator':<14} {'Info Type':<16} Description")
        print(f"  {'─'*70}")
        rows = con.execute(
            "SELECT designator, info_type, description FROM ref.emission_lookup ORDER BY info_type, designator"
        ).fetchall()
        for r in rows:
            print(f"  {r[0]:<14} {r[1]:<16} {r[2]}")
        print(f"  {'─'*70}")
    else:
        print("  ⚠  Invalid choice.")

def search_by_frn(con):
    print("\n--- FRN Search ---")
    print("  FRN ties ALL licenses for one entity together — across all call signs!")
    print("  Find the FRN in any search result, then use it here.\n")

    frn = input("  Enter FRN (e.g. 0006610380): ").strip()

    # First show a summary of all call signs under this FRN
    callsigns = con.execute("""
        SELECT DISTINCT hd.call_sign
        FROM hd
        WHERE hd.unique_system_id IN (
            SELECT unique_system_id FROM en
            WHERE frn = ?
               OR CAST(frn AS INTEGER) = CAST(? AS INTEGER)
        )
        AND hd.call_sign IS NOT NULL AND hd.call_sign != ''
        ORDER BY hd.call_sign
    """, (frn, frn)).fetchall()

    # Get entity name
    entity = con.execute("""
        SELECT DISTINCT entity_name FROM en
        WHERE (frn = ? OR CAST(frn AS INTEGER) = CAST(? AS INTEGER))
          AND entity_type = 'L'
          AND entity_name IS NOT NULL
        LIMIT 1
    """, (frn, frn)).fetchone()

    entity_name = entity[0] if entity else "Unknown"
    cs_list = [r[0] for r in callsigns if r[0]]

    print(f"\n{'='*70}")
    print(f"  FRN: {frn}")
    print(f"  Entity: {entity_name}")
    if cs_list:
        print(f"  Call Signs ({len(cs_list)}): {'  '.join(cs_list)}")
    print(f"{'='*70}")

    # Get all transmitter sites — include ones without coords too
    rows = con.execute(
        base_query() + """
        WHERE lo.unique_system_id IN (
            SELECT unique_system_id FROM en
            WHERE frn = ?
               OR CAST(frn AS INTEGER) = CAST(? AS INTEGER)
        )
        GROUP BY lo.unique_system_id, lo.location_number
        ORDER BY lo.location_state, lo.location_city
        """,
        (frn, frn)
    ).fetchall()

    print_results(con, rows, f"All transmitter sites for FRN {frn} — {entity_name}")

    if rows:
        save = input("\n  Save to file? (y/n): ").strip().lower()
        if save == 'y':
            save_results(con, rows, f"results_frn_{frn}.txt")


def search_by_frn(con):
    print("\n--- FRN Search ---")
    print("  FRN ties ALL licenses for one entity together — across all call signs!")
    print("  Find the FRN in any search result, then use it here.\n")

    frn = input("  Enter FRN (e.g. 0006610380): ").strip()

    # First show a summary of all call signs under this FRN
    callsigns = con.execute("""
        SELECT DISTINCT hd.call_sign
        FROM hd
        WHERE hd.unique_system_id IN (
            SELECT unique_system_id FROM en
            WHERE frn = ?
               OR CAST(frn AS INTEGER) = CAST(? AS INTEGER)
        )
        AND hd.call_sign IS NOT NULL AND hd.call_sign != ''
        ORDER BY hd.call_sign
    """, (frn, frn)).fetchall()

    # Get entity name
    entity = con.execute("""
        SELECT DISTINCT entity_name FROM en
        WHERE (frn = ? OR CAST(frn AS INTEGER) = CAST(? AS INTEGER))
          AND entity_type = 'L'
          AND entity_name IS NOT NULL
        LIMIT 1
    """, (frn, frn)).fetchone()

    entity_name = entity[0] if entity else "Unknown"
    cs_list = [r[0] for r in callsigns if r[0]]

    print(f"\n{'='*70}")
    print(f"  FRN: {frn}")
    print(f"  Entity: {entity_name}")
    if cs_list:
        print(f"  Call Signs ({len(cs_list)}): {'  '.join(cs_list)}")
    print(f"{'='*70}")

    # Get all transmitter sites — include ones without coords too
    rows = con.execute(
        base_query() + """
        WHERE lo.unique_system_id IN (
            SELECT unique_system_id FROM en
            WHERE frn = ?
               OR CAST(frn AS INTEGER) = CAST(? AS INTEGER)
        )
        GROUP BY lo.unique_system_id, lo.location_number
        ORDER BY lo.location_state, lo.location_city
        """,
        (frn, frn)
    ).fetchall()

    print_results(con, rows, f"All transmitter sites for FRN {frn} — {entity_name}")

    if rows:
        save = input("\n  Save to file? (y/n): ").strip().lower()
        if save == 'y':
            save_results(con, rows, f"results_frn_{frn}.txt")


def search_amateur(con):
    print("\n--- Amateur Radio Callsign Lookup ---")
    print("  3,346,184 licensed hams — fully offline!!\n")
    print("  1 - Look up by call sign")
    print("  2 - Look up by last name + state")
    print("  3 - Look up by FRN")

    choice = input("\n  Enter choice (1-3): ").strip()

    if choice == "1":
        call = input("  Enter call sign (e.g. KJ7TNY): ").strip().upper()
        rows = con.execute("""
            SELECT call_sign, full_name, first_name, last_name,
                   city, state, zip_code, operator_class,
                   class_code, group_code, grant_date,
                   expired_date, frn, status
            FROM amateur
            WHERE call_sign = ?
        """, (call,)).fetchall()

        if not rows:
            print(f"  ⚠  No record found for {call}")
            return

        for r in rows:
            _print_ham(r)

    elif choice == "2":
        last  = input("  Last name (partial ok): ").strip()
        state = input("  State code (e.g. ID): ").strip().upper()
        rows = con.execute("""
            SELECT call_sign, full_name, first_name, last_name,
                   city, state, zip_code, operator_class,
                   class_code, group_code, grant_date,
                   expired_date, frn, status
            FROM amateur
            WHERE UPPER(last_name) LIKE UPPER(?)
              AND state = ?
            ORDER BY last_name, first_name
            LIMIT 25
        """, (f"%{last}%", state)).fetchall()

        if not rows:
            print(f"  ⚠  No records found for {last} in {state}")
            return

        print(f"\n  Found {len(rows)} result(s):\n")
        for r in rows:
            _print_ham(r)

    elif choice == "3":
        frn = input("  Enter FRN: ").strip()
        rows = con.execute("""
            SELECT call_sign, full_name, first_name, last_name,
                   city, state, zip_code, operator_class,
                   class_code, group_code, grant_date,
                   expired_date, frn, status
            FROM amateur
            WHERE frn = ?
               OR CAST(frn AS INTEGER) = CAST(? AS INTEGER)
            ORDER BY call_sign
        """, (frn, frn)).fetchall()

        if not rows:
            print(f"  ⚠  No records found for FRN {frn}")
            return

        for r in rows:
            _print_ham(r)
    else:
        print("  ⚠  Invalid choice.")


def _print_ham(r):
    """Print a single ham record nicely."""
    # Status decoder
    status_map = {
        "HA": "Active",
        "HV": "Active (Vanity)",
        "HX": "Expired",
        "HB": "Cancelled",
        "A":  "Active",
        "L":  "Active",
    }
    status_str = status_map.get(r[13], r[13] or "Unknown")
    # Class decoder — blank AM record = General
    class_map = {
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
    class_str = class_map.get(r[8], r[7] or "Unknown")

    print(f"  {'━'*55}")
    print(f"  Call Sign : {r[0]}")
    print(f"  Name      : {r[1] or f'{r[2]} {r[3]}'.strip()}")
    print(f"  Location  : {r[4]}, {r[5]}  {r[6]}")
    print(f"  Class     : {class_str}  (Group {r[9]})" if r[9] else f"  Class     : {class_str}")
    print(f"  Licensed  : {r[10]}")
    if r[11]:
        print(f"  Expires   : {r[11]}")
    print(f"  FRN       : {r[12] or 'N/A'}")
    print(f"  Status    : {status_str}")
    print(f"  {'━'*55}")

def main():
    con = connect()

    total_lo   = con.execute("SELECT COUNT(*) FROM lo").fetchone()[0]
    total_hd   = con.execute("SELECT COUNT(*) FROM hd").fetchone()[0]
    has_em     = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='em'").fetchone() is not None
    has_cities = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cities'").fetchone() is not None
    has_ref    = os.path.exists(REF_DB)


    print(f"\n{'='*55}")
    print("  FCC ULS Transmitter Search")
    print(f"{'='*55}")
    print(f"  Active licenses   : {total_hd:,}")
    print(f"  Transmitter sites : {total_lo:,}")
    print(f"  Emission data     : {'✓ loaded' if has_em     else '✗ run add_em.py'}")
    print(f"  City lookup       : {'✓ loaded' if has_cities else '✗ run add_cities.py'}")
    print(f"  Reference DB      : {'✓ loaded' if has_ref    else '✗ run build_reference.py'}")

    print(f"{'='*55}")

    while True:
        print("\n  What would you like to search?")
        print("  1  - State + County")
        print("  2  - Radius search by coordinates")
        print("  3  - Call sign lookup  (Part 90)")
        print("  4  - Company / licensee name")
        print("  5  - Radius search by city name  ← offline!")
        print("  6  - Frequency range / single frequency search")
        print("  7  - Repeater finder")
        print("  8  - FRN search  ← find everything for one entity!")
        print("  9  - Reference lookup  ← decode emission & station class!")
        print("  10 - Exit")

        choice = input("\n  Enter choice (1-10): ").strip()

        if   choice == "1":  search_by_county(con)
        elif choice == "2":  search_by_radius(con)
        elif choice == "3":  search_by_callsign(con)
        elif choice == "4":  search_by_name(con)
        elif choice == "5":  search_by_city(con)
        elif choice == "6":  search_by_frequency_range(con)
        elif choice == "7":  search_repeaters(con)
        elif choice == "8":  search_by_frn(con)
        elif choice == "9":  search_reference(con)
        elif choice == "10":
            print("\n  Goodbye! Happy scanning! 📻\n")
            break
        else:
            print("  Please enter 1 through 10")

    con.close()


if __name__ == "__main__":
    main()
