#!/usr/bin/env python3
"""
FCC Reference Database Builder
================================
Builds fcc_reference.db with:
  - Emission designator lookup table (decode any emission code)
  - Station class lookup table (decode FB2, MO3, FX1 etc)

Run this ONCE — this database never gets wiped or rebuilt.
It is permanent reference data that never changes.

Usage:
    python3 build_reference.py
"""

import sqlite3
import os

REF_DB = os.path.expanduser("~/fcc-scanner/fcc_reference.db")

# ---------------------------------------------------------------
# EMISSION DESIGNATORS
# Format: (code, bandwidth, modulation, info_type, description)
#
# Emission designator structure:
#   Characters 1-4 : Bandwidth  (e.g. 11K2 = 11.25 kHz, 8K10 = 8.1 kHz)
#   Character  5   : Modulation type
#   Character  6   : Nature of modulating signal
#   Character  7   : Type of information
#
# Modulation types (char 5):
#   A = AM double sideband
#   B = AM independent sideband
#   C = AM vestigial sideband
#   D = Carrier varies (AM+FM combined)
#   F = FM
#   G = Phase modulation
#   H = AM single sideband full carrier
#   J = AM single sideband suppressed carrier
#   K = Pulse amplitude
#   L = Pulse width
#   M = Pulse phase/position
#   N = Unmodulated carrier
#   P = Sequence of pulses, no modulation
#   Q = Sequence of pulses, angle modulated
#   R = AM single sideband reduced carrier
#   V = Combination of above
#   W = Combination of above
#   X = Other
#
# Nature of signal (char 6):
#   0 = No modulating signal
#   1 = Digital, single channel, no subcarrier
#   2 = Digital, single channel, with subcarrier
#   3 = Analog, single channel
#   7 = Digital, multiple channels
#   8 = Analog, multiple channels
#   9 = Analog+Digital combined
#   X = Other
#
# Type of information (char 7):
#   N = No information
#   A = Telegraphy (Morse)
#   B = Telegraphy (machine)
#   C = Facsimile
#   D = Data, telemetry, telecommand
#   E = Telephony (voice)
#   F = Television (video)
#   W = Combination of above
#   X = Other
# ---------------------------------------------------------------

EMISSION_DESIGNATORS = [
    # Common Part 90 / Land Mobile emissions
    ("11K2F3E", "11.25 kHz",  "FM",           "Voice",        "FM Analog Voice — standard 12.5 kHz channel"),
    ("20K0F3E", "20.0 kHz",   "FM",           "Voice",        "FM Analog Voice — standard 25 kHz channel (wideband)"),
    ("16K0F3E", "16.0 kHz",   "FM",           "Voice",        "FM Analog Voice — 16 kHz channel"),
    ("11K0F3E", "11.0 kHz",   "FM",           "Voice",        "FM Analog Voice — narrow 11 kHz channel"),
    ("8K10F3E", "8.1 kHz",    "FM",           "Voice",        "FM Analog Voice — 8.1 kHz narrowband"),
    ("6K00F3E", "6.0 kHz",    "FM",           "Voice",        "FM Analog Voice — 6 kHz narrowband"),
    ("11K3F3E", "11.3 kHz",   "FM",           "Voice",        "FM Analog Voice — 11.3 kHz channel"),
    ("11K2F1E", "11.25 kHz",  "FM",           "Digital Voice","FM Digital Voice — 12.5 kHz channel"),
    ("8K10F1E", "8.1 kHz",    "FM",           "Digital Voice","FM Digital Voice — P25 Phase II / NXDN"),
    ("7K60FXE", "7.6 kHz",    "FM",           "Digital Voice","FM Digital Voice — NXDN 6.25 kHz / P25 Phase II"),
    ("4K00F1E", "4.0 kHz",    "FM",           "Digital Voice","FM Digital Voice — NXDN 4 kHz narrowband"),
    ("8K30F7W", "8.3 kHz",    "FM",           "Digital Mixed","FM Digital Voice — P25 Phase II mixed"),
    ("4K00F7W", "4.0 kHz",    "FM",           "Digital Mixed","FM Digital Voice — digital mixed mode"),
    ("11K2F1D", "11.25 kHz",  "FM",           "Digital Data", "FM Digital Data — 12.5 kHz channel"),
    ("8K10F1D", "8.1 kHz",    "FM",           "Digital Data", "FM Digital Data — P25 Phase II data"),
    ("7K60FXD", "7.6 kHz",    "FM",           "Digital Data", "FM Digital Data — NXDN data"),
    ("4K00F1D", "4.0 kHz",    "FM",           "Digital Data", "FM Digital Data — narrowband data"),
    ("6K00F2D", "6.0 kHz",    "FM",           "Digital Data", "FM Digital Data — with subcarrier"),
    ("11K2F2D", "11.25 kHz",  "FM",           "Digital Data", "FM Digital Data — with subcarrier"),
    ("8K10F2D", "8.1 kHz",    "FM",           "Digital Data", "FM Digital Data — with subcarrier"),
    ("11K2F9W", "11.25 kHz",  "FM",           "Mixed",        "FM Mixed Analog+Digital — dual mode radio"),
    ("20K0F9W", "20.0 kHz",   "FM",           "Mixed",        "FM Mixed Analog+Digital — wideband dual mode"),
    ("11K2F7W", "11.25 kHz",  "FM",           "Mixed",        "FM Digital Multi-channel mixed"),
    ("8K10F7W", "8.1 kHz",    "FM",           "Mixed",        "FM Digital Multi-channel mixed"),
    ("7K60FXW", "7.6 kHz",    "FM",           "Mixed",        "FM Digital Mixed — NXDN/P25 II mixed"),
    ("20K0F2D", "20.0 kHz",   "FM",           "Digital Data", "FM Digital Data — 800 MHz trunked"),
    ("20K0F1D", "20.0 kHz",   "FM",           "Digital Data", "FM Digital Data — wideband"),
    ("20K0F7W", "20.0 kHz",   "FM",           "Mixed",        "FM Digital Mixed — 800 MHz trunked"),
    # P25 specific
    ("8K10F1W", "8.1 kHz",    "FM",           "Digital Mixed","P25 Phase II TDMA Digital Voice/Data"),
    ("9K36F1W", "9.36 kHz",   "FM",           "Digital Mixed","P25 Phase I C4FM Digital Voice"),
    ("12K5F1W", "12.5 kHz",   "FM",           "Digital Mixed","P25 Phase I Digital Voice/Data"),
    ("12K5F1E", "12.5 kHz",   "FM",           "Digital Voice","P25 Phase I Digital Voice"),
    # DMR / MotoTRBO
    ("7K60FXE", "7.6 kHz",    "FM",           "Digital Voice","DMR / MotoTRBO Digital Voice 6.25 kHz equiv"),
    # APCO-25 / OpenSky
    ("11K5F1W", "11.5 kHz",   "FM",           "Digital Mixed","P25 / OpenSky Digital"),
    # Paging
    ("11K2F2D", "11.25 kHz",  "FM",           "Paging Data",  "FM Paging / Data with subcarrier"),
    ("20K0F2D", "20.0 kHz",   "FM",           "Paging Data",  "FM Paging / Data wideband"),
    # AM
    ("8K00A3E", "8.0 kHz",    "AM",           "Voice",        "AM Analog Voice — aircraft/maritime"),
    ("6K00A3E", "6.0 kHz",    "AM",           "Voice",        "AM Analog Voice — narrowband"),
    # Microwave / point to point
    ("10M0W7W", "10.0 MHz",   "Combined",     "Mixed",        "Microwave — point to point link (wideband)"),
    ("10M0W7D", "10.0 MHz",   "Combined",     "Digital Data", "Microwave — point to point digital data"),
    ("10M0D7W", "10.0 MHz",   "Carrier",      "Mixed",        "Microwave — digital point to point"),
    ("10M0X7W", "10.0 MHz",   "Other",        "Mixed",        "Microwave — broadband link"),
    ("5M00X7W", "5.0 MHz",    "Other",        "Mixed",        "Microwave — narrower point to point"),
    ("3M00X7W", "3.0 MHz",    "Other",        "Mixed",        "Microwave — point to point 3 MHz"),
    ("2M00X7W", "2.0 MHz",    "Other",        "Mixed",        "Microwave — point to point 2 MHz"),
    ("1M25X7W", "1.25 MHz",   "Other",        "Mixed",        "Microwave — point to point 1.25 MHz"),
    # Radar / telemetry
    ("32M0P0N", "32.0 MHz",   "Pulse",        "None",         "Radar / pulsed unmodulated"),
    ("P0N",     "varies",     "Pulse",        "None",         "Pulsed carrier — radar"),
    # Television
    ("6M00C3F", "6.0 MHz",    "AM Vestigial", "Video",        "Analog TV — NTSC"),
    # Telemetry
    ("4K00F1D", "4.0 kHz",    "FM",           "Telemetry",    "FM Telemetry / SCADA data"),
    ("11K2F1D", "11.25 kHz",  "FM",           "Telemetry",    "FM Telemetry / data"),
    # SSB voice (amateur / aviation)
    ("2K80J3E", "2.8 kHz",    "SSB",          "Voice",        "SSB Voice — amateur HF / aviation"),
    ("3K00J3E", "3.0 kHz",    "SSB",          "Voice",        "SSB Voice — HF"),
    ("2K70J3E", "2.7 kHz",    "SSB",          "Voice",        "SSB Voice — HF narrowband"),
    # CW / Morse
    ("150HA1A", "150 Hz",     "AM CW",        "Morse",        "CW Morse code — amateur"),
    ("200HA1A", "200 Hz",     "AM CW",        "Morse",        "CW Morse code"),
    # APRS / Packet
    ("16K0F2D", "16.0 kHz",   "FM",           "Packet Data",  "FM Packet / APRS data"),
    ("11K2F2D", "11.25 kHz",  "FM",           "Packet Data",  "FM Packet data"),
    # Spread spectrum
    ("5M00XDD", "5.0 MHz",    "Spread",       "Digital Data", "Spread spectrum digital data"),
    # Additional common
    ("11K2F3D", "11.25 kHz",  "FM",           "Fax/Data",     "FM Analog Fax or slow data"),
    ("8K10F3D", "8.1 kHz",    "FM",           "Fax/Data",     "FM Fax or slow data narrowband"),
    ("11K0F1E", "11.0 kHz",   "FM",           "Digital Voice","FM Digital Voice narrowband"),
    ("11K0F1D", "11.0 kHz",   "FM",           "Digital Data", "FM Digital Data narrowband"),
]

# ---------------------------------------------------------------
# STATION CLASS CODES
# ---------------------------------------------------------------

STATION_CLASSES = [
    # Base/Fixed stations
    ("FB",    "Fixed Base",                    "Base station — transmits to mobile units"),
    ("FB1",   "Fixed Base Primary",            "Primary base station"),
    ("FB2",   "Fixed Base Secondary",          "Repeater OUTPUT — what you hear on scanner"),
    ("FB4",   "Fixed Base 4",                  "Base station — itinerant use"),
    ("FB5",   "Fixed Base 5",                  "Base station — shared use"),
    ("FB6",   "Fixed Base 6",                  "Repeater base — output (trunked systems)"),
    ("FB7",   "Fixed Base 7",                  "Base station — secondary"),
    ("FB8",   "Fixed Base 8",                  "Repeater base output — trunked/simulcast"),
    ("FB2S",  "Fixed Base Secondary Simulcast","Simulcast repeater output site"),
    ("FBT",   "Fixed Base Temporary",          "Temporary base station — portable/deployable"),
    # Fixed relay / repeater inputs
    ("FX",    "Fixed Station",                 "Fixed point-to-point link or control station"),
    ("FX1",   "Fixed Relay Primary",           "Repeater INPUT — what radios transmit into"),
    ("FX2",   "Fixed Relay Secondary",         "Secondary repeater input — cross-band link"),
    ("FXO",   "Fixed Relay Other",             "Fixed relay — other type"),
    ("FXB",   "Fixed Relay Broadband",         "Fixed broadband relay — microwave link"),
    # Mobile stations
    ("MO",    "Mobile",                        "Standard mobile unit — vehicle or portable"),
    ("MO1",   "Mobile Primary",                "Primary mobile unit"),
    ("MO2",   "Mobile Secondary",              "Secondary mobile unit"),
    ("MO3",   "Mobile Vehicle Repeater",       "Vehicle-mounted repeater — extends coverage"),
    ("MO4",   "Mobile Itinerant",              "Mobile itinerant — moves between areas"),
    ("MOI",   "Mobile Itinerant",              "Mobile itinerant use"),
    # Aircraft
    ("AO",    "Aircraft",                      "Airborne mobile station"),
    ("AOM",   "Aircraft Mobile",               "Aircraft mobile unit"),
    # Ship/Marine
    ("SO",    "Ship",                          "Ship station"),
    ("CS",    "Coast Station",                 "Coast/shore station for marine"),
    # Portable/Handheld
    ("PO",    "Portable",                      "Handheld portable unit"),
    # Control/Dispatch
    ("FC",    "Fixed Control",                 "Remote control point / dispatch console"),
    ("FB2S",  "Simulcast Secondary",           "Simulcast repeater output"),
    # Paging
    ("FB2P",  "Fixed Base Paging",             "One-way paging transmitter"),
    ("MOP",   "Mobile Paging",                 "Mobile paging receiver"),
    # Itinerant
    ("IT",    "Itinerant",                     "Itinerant — no fixed location, moves around"),
    # Microwave
    ("TS",    "Terminal Station",              "Microwave terminal station"),
    ("RS",    "Repeater Station",              "Microwave repeater station"),
    ("LS",    "Link Station",                  "Microwave link station"),
    # Other
    ("GL",    "Ground",                        "Ground station"),
    ("GS",    "Ground Support",                "Ground support station"),
    # MO variants
    ("MO5",   "Mobile & Temporary Fixed",      "Mobile and temporary fixed combined"),
    ("MO6",   "Private Carrier Mobile",        "Private carrier mobile — for-profit operation"),
    ("MO6C",  "Private Carrier Mobile Interconn","Private carrier mobile with interconnect"),
    ("MO6I",  "Private Carrier Mobile Itinerant","Private carrier mobile itinerant"),
    ("MO6K",  "Private Carrier Mobile Standby", "Private carrier mobile standby"),
    ("MO8",   "Centralized Trunk Mobile",       "Trunked system mobile — paired with FB8"),
    ("MO3C",  "Vehicle Repeater Interconnect",  "Vehicle repeater with phone interconnect"),
    ("MO3I",  "Vehicle Repeater Itinerant",     "Vehicle repeater itinerant use"),
    ("MO3S",  "Vehicle Repeater Standby",       "Vehicle repeater standby"),
    ("MO3T",  "Vehicle Repeater Temporary",     "Vehicle repeater temporary use"),
    ("MOI",   "Mobile Itinerant",               "Mobile itinerant — no fixed area"),
    # FB variants
    ("FB2S",  "Simulcast Repeater Output",      "Simulcast repeater output — multiple sites same freq"),
    ("FB6",   "Trunked Repeater Output",        "Trunked system repeater output 150-512 MHz"),
    # FX variants  
    ("FXO",   "Fixed Relay Other",              "Fixed relay — other category"),
    ("FXB",   "Fixed Relay Broadband",          "Microwave broadband relay link"),
    ("FXZT",  "Zone Temporary",                 "Zone station temporary"),
    ("FXZS",  "Zone Standby",                   "Zone station standby"),
    # Aviation
    ("AO",    "Aircraft",                       "Airborne mobile station"),
    ("AOM",   "Aircraft Mobile",                "Aircraft mobile unit"),
    ("MFL",   "Aeronautical Multicom",          "Aeronautical multicom station"),
    ("MFL1",  "Aeronautical Multicom Mobile",   "Aeronautical multicom mobile"),
    # Marine
    ("SO",    "Ship Station",                   "Ship mobile station"),
    ("CS",    "Coast Station",                  "Shore/coast station for marine comms"),
    ("MFX",   "Marine Fixed",                   "Marine operations fixed station"),
    ("MFX2",  "Marine Fixed Temporary",         "Marine fixed temporary"),
    # Paging
    ("FB2P",  "Paging Transmitter",             "One-way paging base transmitter"),
    # Control
    ("FC",    "Fixed Control",                  "Remote control / dispatch console"),
    ("GCO",   "Ground Communications Outlet",   "Ground comm outlet — aviation"),
    # Radiolocation
    ("LR",    "Radiolocation Land",             "Land radiolocation station"),
    ("LRI",   "Radiolocation Land Itinerant",   "Land radiolocation itinerant"),
]

def build_reference_db():
    print(f"\n{'='*55}")
    print("  FCC Reference Database Builder")
    print(f"{'='*55}")
    print(f"  Output: {REF_DB}\n")

    con = sqlite3.connect(REF_DB)
    con.execute("PRAGMA journal_mode=WAL")

    # ── Emission Designator Table ──────────────────────────────
    con.executescript("""
        DROP TABLE IF EXISTS emission_lookup;
        CREATE TABLE emission_lookup (
            designator   TEXT PRIMARY KEY,
            bandwidth    TEXT,
            modulation   TEXT,
            info_type    TEXT,
            description  TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_em_lookup ON emission_lookup(designator);
    """)

    con.executemany(
        "INSERT OR REPLACE INTO emission_lookup VALUES (?,?,?,?,?)",
        EMISSION_DESIGNATORS
    )
    con.commit()
    print(f"  ✓ Emission designators : {len(EMISSION_DESIGNATORS)} codes loaded")

    # ── Station Class Table ────────────────────────────────────
    con.executescript("""
        DROP TABLE IF EXISTS station_class;
        CREATE TABLE station_class (
            code         TEXT PRIMARY KEY,
            name         TEXT,
            description  TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_sc_code ON station_class(code);
    """)

    con.executemany(
        "INSERT OR REPLACE INTO station_class VALUES (?,?,?)",
        STATION_CLASSES
    )
    con.commit()
    print(f"  ✓ Station class codes  : {len(STATION_CLASSES)} codes loaded")

    con.execute("ANALYZE")
    con.close()

    size = os.path.getsize(REF_DB) / 1024
    print(f"\n{'='*55}")
    print(f"  ✓  Done!  Reference DB: {size:.1f} KB")
    print(f"  Saved to: {REF_DB}")
    print(f"{'='*55}")
    print("\n  This database never needs to be rebuilt!")
    print("  Run search_fcc.py to use the reference lookups.\n")


if __name__ == "__main__":
    build_reference_db()
