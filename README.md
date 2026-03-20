# FCC ULS Private Land Mobile — Offline Transmitter Search Tool
### "I Will Find You" — by Minty & The Wizard 🧙‍♂️📻

---

## What This Is

A fully offline FCC transmitter search tool that searches the **actual transmitter locations**
(antenna sites with GPS coordinates) instead of the licensee's home office address like the
FCC website does. Built on SQLite with Python scripts running on Linux Mint.

**The problem this solves:** The FCC ULS website searches by licensee address. A company
headquartered in California with a store in Clarkston WA won't show up in a Clarkston search.
This tool finds the TRANSMITTER — the actual antenna — wherever it physically is.

---

## What's In This Folder

```
~/fcc-scanner/
├── import_fcc.py       ← Step 1: Import FCC data files into database
├── reload_fr.py        ← Step 2: Fix frequency table (run after import)
├── add_em.py           ← Step 3: Add emission designators
├── add_cities.py       ← Step 4: Add offline city coordinates (run once)
├── search_fcc.py       ← THE MAIN TOOL — run this to search!
├── uscities.csv        ← US cities database (31,257 cities with GPS coords)
├── fcc.db              ← The SQLite database (2.4GB — rebuilt from data files)
├── data/               ← FCC .dat files go here (downloaded from FCC)
│   ├── HD.dat
│   ├── EN.dat
│   ├── LO.dat
│   ├── FR.dat
│   ├── EM.dat
│   └── (other FCC files)
└── reports/            ← All saved search results go here (timestamped)
```

---

## First Time Setup (Start Here)

### Step 1 — Download the FCC Data

Go to this URL and download the **Private Land Mobile** complete weekly zip:

```
https://data.fcc.gov/download/pub/uls/complete/a_LMpriv.zip
```

Unzip it into your data folder:
```bash
unzip ~/Downloads/a_LMpriv.zip -d ~/fcc-scanner/data/
```

### Step 2 — Download the Cities Database (one time only)

Go to: `https://simplemaps.com/data/us-cities`
Download the free version — it will be a zip containing `uscities.csv`
Put `uscities.csv` in `~/fcc-scanner/`

### Step 3 — Build the Database

Run these scripts IN ORDER:

```bash
cd ~/fcc-scanner
python3 import_fcc.py
python3 reload_fr.py
python3 add_em.py
python3 add_cities.py
```

**What each script does:**
- `import_fcc.py` — reads all .dat files and builds the SQLite database (~15-20 min)
- `reload_fr.py` — fixes the frequency table column mapping (required after import)
- `add_em.py` — adds emission designators (analog/digital info) (~5 min)
- `add_cities.py` — loads 31,257 US cities with GPS coordinates (instant)

When done you should see:
```
Active licenses   : 2,827,785
Transmitter sites : 1,347,539
Emission data     : ✓ loaded
City lookup       : ✓ loaded
```

---

## Running the Search Tool

```bash
cd ~/fcc-scanner
python3 search_fcc.py
```

### Search Options

```
1 - State + County
    Search all transmitters physically located in a county.
    Example: WA + Asotin → finds every antenna in Asotin County WA
    Note: uses transmitter location, NOT licensee home address!

2 - Radius search by coordinates
    Enter decimal lat/lon (from Google Maps right-click) + miles radius
    Example: 46.4161, -117.0505, 5 miles

3 - Call sign lookup
    Enter a call sign like WQMD311 → shows ALL transmitter sites
    for that license nationwide, each with its own frequencies

4 - Company / licensee name search
    Partial name search — type "Walmart" or "City of" etc.
    Shows all transmitter sites for matching companies

5 - Radius search by city name  ← OFFLINE, no internet needed!
    Type a city name + state code → looks up GPS coords from local
    cities database → does radius search automatically
    Example: Lewiston + ID + 5 miles

6 - Frequency range search
    Find every transmitter on a specific band in your area
    Common ranges:
      VHF Low  :  30 -  50 MHz  (old fire/police)
      VHF High : 150 - 174 MHz  (fire, EMS, business)
      UHF      : 450 - 470 MHz  (business, GMRS)
      800 MHz  : 806 - 869 MHz  (trunked systems)
    Can search by city, coordinates, or county

7 - Repeater finder
    Finds licenses that have BOTH FB2 (output) and FX1 (input)
    Groups all outputs and inputs per license
    Shows offset between input and output frequencies
    Labels standard offsets: ★ Standard UHF (5 MHz), ★ Gov UHF (9 MHz),
    ★ 800 MHz (45 MHz), ★ 700 MHz (30 MHz), ★ Ham VHF (0.6 MHz)
    Can search by city, coordinates, county, or frequency range

8 - Exit
```

### Understanding the Results

**Frequency columns:**
```
154.20500 MHz | FB2  | 75.0W   | 20K0F3E (FM Analog Voice)
  frequency     class   power     emission designator
```

**Station Classes:**
- `FB`  = Fixed Base station
- `FB2` = Fixed Base secondary (REPEATER OUTPUT — what you hear)
- `FX1` = Fixed relay (REPEATER INPUT — what radios transmit into)
- `FX`  = Fixed station / point to point link
- `MO`  = Mobile unit
- `FBT` = Temporary base

**Emission Designators (last 3 characters):**
- `F3E` = FM Analog Voice ← your scanner can hear this!
- `F1E` = FM Digital Voice (needs digital decoder)
- `F1D` = FM Digital Data
- `F7E` = FM Digital Voice
- `FXE` = Digital NXDN/P25 (needs digital decoder)
- `P0N` = Pulsed/Radar

**Repeater offsets:**
- Positive offset = input is higher than output
- Negative offset = input is lower than output
- `★ Standard UHF` = exactly 5.000 MHz (most UHF business)
- `★ Gov UHF` = exactly 9.000 MHz (government UHF)
- `★ 800 MHz` = 45 MHz offset
- `★ 700 MHz` = 30 MHz offset
- `★ Ham VHF` = 0.6 MHz (ham repeaters on 144-148 MHz)
- VHF High (150-174 MHz) = anything goes, no standard offset!

---

## Updating the Database

The FCC releases new data weekly. Update whenever you want fresh data.

### Update Steps

1. Download fresh zip from FCC:
   ```
   https://data.fcc.gov/download/pub/uls/complete/a_LMpriv.zip
   ```

2. Unzip into data folder (overwrites old files):
   ```bash
   unzip ~/Downloads/a_LMpriv.zip -d ~/fcc-scanner/data/
   ```

3. Run the import scripts again:
   ```bash
   cd ~/fcc-scanner
   python3 import_fcc.py
   python3 reload_fr.py
   python3 add_em.py
   ```

**Note:** You do NOT need to re-run `add_cities.py` — city coordinates
don't change! Only run it if the uscities.csv file gets updated.

**Note:** The FCC URL sometimes changes. If the download link breaks,
search for "FCC ULS complete database download private land mobile"
to find the current URL.

---

## Saved Reports

All saved searches go to `~/fcc-scanner/reports/` with timestamps:
```
results_WA_Asotin_20260318_143022.txt
results_freq_150.0-174.0_Lewiston_20260318_160512.txt
repeaters_Clarkston_WA_within_5_0_miles_20260320_154835.txt
```

The timestamp format is `YYYYMMDD_HHMMSS` so files sort chronologically.
You can run the same search multiple times and compare results over time
to see what licenses are added or removed between database updates.

---

## Database Stats (as of March 2026 build)

| Table | Records | Description |
|-------|---------|-------------|
| hd    | 2,827,785 | License headers |
| en    | 5,077,667 | Licensee/entity names |
| lo    | 1,347,539 | Transmitter locations with GPS |
| fr    | 5,185,935 | Frequency assignments |
| em    | 10,446,808 | Emission designators |
| cities | 31,257   | US cities for offline lookup |

---

## Backing Up This Project

**Back up these files** (scripts and cities database):
```bash
cp ~/fcc-scanner/*.py ~/your-backup-location/
cp ~/fcc-scanner/uscities.csv ~/your-backup-location/
```

**Do NOT need to back up:**
- `fcc.db` — 2.4GB, rebuilt from FCC download any time
- `data/*.dat` — FCC source files, re-downloaded from FCC

**GitHub:** Push the Python scripts and uscities.csv to a GitHub repo.
The database is too large for GitHub (2.4GB limit is 100MB per file)
but the scripts are all you need — the database rebuilds in ~25 minutes.

---

## Troubleshooting

**"Database not found"**
→ Run import_fcc.py first

**"City not found"**
→ Try a nearby larger city, or use option 2 (coordinates) instead

**Search returns 0 results**
→ Check state code is 2 letters (WA not Washington)
→ County name can be partial — "Asotin" not "Asotin County"

**Search is slow**
→ Normal on first run while SQLite warms up indexes
→ Results appear all at once after thinking — it's working!

**FCC download URL broken**
→ Go to fcc.gov and search for "ULS database download"
→ Look for "Private Land Mobile" complete weekly file

**Frequencies show (none on file)**
→ Some licenses file location records without frequency records
→ The transmitter site is real, frequencies just weren't filed

---

## Tips & Tricks

- **Cross-reference with your scanner:** Find a frequency on your scanner,
  use option 6 (frequency range) to look it up and identify who it is

- **Coordinate trick:** Copy coords from any result and paste into
  option 2 to search around that exact tower location

- **Repeater cross-band links:** If you see an offset of 200+ MHz
  in the repeater finder, it's a cross-band link (receives on one
  band, retransmits on another) — common in mountainous areas

- **Multiple locations same call sign:** One license can have 100+
  transmitter sites nationwide — option 3 (call sign) shows them all
  each with their own specific frequencies

- **FX1 as base station:** Some licensees incorrectly file base stations
  as FX1 instead of FB. If you see FX1 with no FB2 match, it may
  actually be a base station, not a repeater input

---

*Built March 2026 — Linux Mint — Python 3.12 — SQLite*
*"I Will Find You" 📻🚀*
