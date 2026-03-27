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

## The Tool Ecosystem — "The Jailhouse"

```
fcc.db  ←  THE JAILHOUSE  (holds all the data prisoners)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  hd, en, lo, fr, em   ← Part 90 Land Mobile data
  cities               ← 31,257 US city coordinates
  amateur              ← 3.3M ham radio callsigns
  gmrs                 ← 578k gmrs radio callsigns
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

fcc_reference.db  ←  PERMANENT REFERENCE (never rebuilt)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  emission_lookup      ← decode any emission designator
  station_class        ← decode any station class code
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TOOLS THAT ACCESS THE JAILHOUSE:
  search_fcc.py  ← Part 90 scanner radio search tool
  hamcall.py     ← Amateur / gmrs callsign GUI lookup
  (more tools coming as the project grows!!)
```

---

## What's In This Folder

```
~/fcc-scanner/
├── import_fcc.py       ← Step 1: Import FCC Private Land Mobile data
├── reload_fr.py        ← Step 2: Fix frequency table (run after import)
├── add_em.py           ← Step 3: Add emission designators
├── add_cities.py       ← Step 4: Add offline city coordinates (run once)
├── build_reference.py  ← Step 5: Build permanent reference database (run once)
├── import_amateur.py   ← Step 6: Import amateur radio callsign database
├── import_gmrs.py   ← Step 7: Import gmrs radio callsign database
├── search_fcc.py       ← Part 90 search tool (terminal)
├── hamcall.py          ← Ham callsign lookup (GUI desktop app!!)
├── uscities.csv        ← US cities database (31,257 cities with GPS coords)
├── fcc.db              ← Main SQLite database (2.4GB+ — rebuilt from data files)
├── fcc_reference.db    ← Permanent reference database (tiny, never rebuilt)
├── data/               ← FCC Private Land Mobile .dat files
│   ├── HD.dat
│   ├── EN.dat
│   ├── LO.dat
│   ├── FR.dat
│   ├── EM.dat
│   └── (other FCC files)
├── amateur/            ← FCC Amateur Radio .dat files
│   ├── HD.dat
│   ├── EN.dat
│   ├── AM.dat
│   └── (other FCC files)
├── gmrs/            ← FCC Amateur Radio .dat files
│   ├── HD.dat
│   ├── EN.dat
│   ├── AM.dat
│   └── (other FCC files)
└── reports/            ← All saved search results go here (timestamped)
```

---

## First Time Setup (Start Here)

### Step 1 — Download the FCC Private Land Mobile Data

```
https://data.fcc.gov/download/pub/uls/complete/a_LMpriv.zip
```

```bash
unzip ~/Downloads/a_LMpriv.zip -d ~/fcc-scanner/data/
```

### Step 2 — Download the Cities Database (one time only)

Go to: `https://simplemaps.com/data/us-cities`
Download the free version — zip contains `uscities.csv`
Put `uscities.csv` in `~/fcc-scanner/`

### Step 3 — Download the Amateur Radio Database

```
https://data.fcc.gov/download/pub/uls/complete/a_amat.zip
```

```bash
unzip ~/Downloads/a_amat.zip -d ~/fcc-scanner/amateur/
```

### Step 4 — Install tkinter (one time only — needed for HamCall GUI)

```bash
sudo apt install python3-tk
```

### Step 5 — Build All the Databases

Run these scripts IN ORDER:

```bash
cd ~/fcc-scanner
python3 import_fcc.py
python3 reload_fr.py
python3 add_em.py
python3 add_cities.py
python3 build_reference.py
python3 import_amateur.py
python3 import_gmrs.py
```

**What each script does:**
- `import_fcc.py` — reads all .dat files and builds the SQLite database (~15-20 min)
- `reload_fr.py` — fixes the frequency table column mapping (required after import)
- `add_em.py` — adds emission designators (~5 min)
- `add_cities.py` — loads 31,257 US cities with GPS coordinates (run ONCE, never again)
- `build_reference.py` — builds permanent emission/station class reference (run ONCE, never again)
- `import_amateur.py` — loads 3.3 million ham callsigns (~5 min, update anytime)
- `import_gmrs.py` — loads 578k gmrs callsigns (~3 min, update anytime)

When done search_fcc.py should show:
```
Active licenses   : 2,827,785
Transmitter sites : 1,347,539
Emission data     : ✓ loaded
City lookup       : ✓ loaded
Reference DB      : ✓ loaded
```

---

## Tool 1 — search_fcc.py (Part 90 Scanner Search)

```bash
cd ~/fcc-scanner
python3 search_fcc.py
```

**Focused entirely on Part 90 Land Mobile — scanner radio research!!**

### Search Options

```
1  - State + County
     Search all transmitters physically located in a county.
     Example: WA + Asotin → finds every antenna in Asotin County WA
     Note: uses transmitter location, NOT licensee home address!

2  - Radius search by coordinates
     Enter decimal lat/lon (from Google Maps right-click) + miles radius
     Example: 46.4161, -117.0505, 5 miles

3  - Call sign lookup (Part 90)
     Enter a call sign → shows ALL transmitter sites for that license
     nationwide, each with its own specific frequencies
     Also shows FRN number for further research

4  - Company / licensee name search
     Partial name search — type "Walmart" or "City of" etc.
     Shows all transmitter sites for matching companies

5  - Radius search by city name  ← OFFLINE, no internet needed!
     Type a city name + state code → looks up GPS coords from local
     cities database → does radius search automatically
     Example: Lewiston + ID + 5 miles

6  - Frequency range / single frequency search
     Find every transmitter on a specific band in your area
     TIP: Press ENTER on high frequency for SINGLE frequency lookup!!
     Common ranges:
       VHF Low  :  30 -  50 MHz  (old fire/police)
       VHF High : 150 - 174 MHz  (fire, EMS, business)
       UHF      : 450 - 470 MHz  (business, GMRS)
       800 MHz  : 806 - 869 MHz  (trunked systems)
     Can search by city, coordinates, or county

7  - Repeater finder
     Finds licenses with BOTH FB2 (output) and FX1 (input)
     Groups all outputs and inputs per license
     Shows offset between input and output frequencies
     Labels standard offsets: ★ Standard UHF (5 MHz), ★ Gov UHF (9 MHz),
     ★ 800 MHz (45 MHz), ★ 700 MHz (30 MHz), ★ Ham VHF (0.6 MHz)
     Can search by city, coordinates, county, or frequency range + city

8  - FRN search  ← find EVERYTHING for one entity!
     FRN (FCC Registration Number) ties ALL licenses together
     Shows summary of ALL call signs under that FRN at the top
     Finds transmitters across multiple call signs for same entity
     Example: Asotin County has 8 call signs under one FRN!

9  - Reference lookup  ← decode emission & station class codes!
     Look up any emission designator (e.g. 8K10F1W → P25 Phase II)
     Look up any station class code (e.g. MO3 → Vehicle Repeater)
     Browse ALL emission designators or station classes
     Fully offline — built once, never needs updating

10 - Exit
```

---

## Tool 2 — hamcall.py (Amateur & GMRS Callsign GUI)

```bash
cd ~/fcc-scanner
python3 hamcall.py
```

**A desktop GUI app for quick ham callsign lookups — completely offline!!**

- Dark terminal aesthetic — green on black radio feel
- Type any callsign, press ENTER — instant results
- Shows name, location, license class, expiration, FRN, status
- 3,346,184 licensed hams in the database
- Active = green, expired/not found = red

**Future phases planned:**
- DX contact logging
- Personal notes on any callsign
- QSO history and profiles
- ADIF export for ham logging software

### Desktop Shortcut for HamCall

```bash
cat > ~/Desktop/HamCall.desktop << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=HamCall
Comment=Amateur - GMRS Callsign Lookup
Exec=python3 /home/minty/fcc-scanner/hamcall.py
Icon=network-wireless
Terminal=false
Categories=HamRadio;
EOF
chmod +x ~/Desktop/HamCall.desktop
```

### Desktop Shortcut for FCC Scanner

```bash
cat > ~/Desktop/FCC-Scanner.desktop << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=FCC Scanner
Comment=FCC ULS Transmitter Search
Exec=bash -c "cd /home/minty/fcc-scanner && python3 search_fcc.py"
Icon=network-wired
Terminal=true
Categories=HamRadio;
EOF
chmod +x ~/Desktop/FCC-Scanner.desktop
```

---

### Understanding search_fcc.py Results

**Frequency columns:**
```
154.20500 MHz | FB2  | 75.0W   | 20K0F3E (FM Analog Voice)
  frequency     class   power     emission designator (auto-decoded!)
```

**FRN shown in every result** — use it with option 8 to find ALL
licenses for that entity across every call sign they hold!!

**Station Classes:**
- `FB`   = Fixed Base station (dispatch console)
- `FB2`  = Fixed Base secondary (**REPEATER OUTPUT** — what you hear on scanner)
- `FB2S` = Simulcast repeater output
- `FB6`  = Trunked repeater output
- `FB8`  = Trunked repeater output (800 MHz systems)
- `FX1`  = Fixed relay primary (**REPEATER INPUT** — what radios transmit into)
- `FX2`  = Fixed relay secondary (cross-band link input)
- `FX`   = Fixed station / point to point link
- `FXB`  = Fixed broadband relay (microwave backbone)
- `MO`   = Standard mobile unit
- `MO3`  = Vehicle-mounted repeater — extends coverage
- `MO8`  = Trunked system mobile (paired with FB8)
- `FBT`  = Temporary base station (deployable)
- Use **option 9** to decode ANY station class instantly!!

**Emission Designators (last 3 characters):**
- `F3E` = FM Analog Voice ← your scanner can hear this!
- `F1E` = FM Digital Voice (P25, NXDN — needs digital decoder)
- `F1D` = FM Digital Data
- `F1W` = FM Digital Mixed (P25 Phase II TDMA)
- `FXE` = Digital NXDN/P25 6.25kHz
- `FXD` = Digital Data NXDN
- `P0N` = Pulsed/Radar
- Use **option 9** to decode ANY emission designator instantly!!

**Repeater offsets:**
- Positive offset = input is HIGHER than output
- Negative offset = input is LOWER than output
- `★ Standard UHF` = exactly 5.000 MHz (most UHF business)
- `★ Gov UHF` = exactly 9.000 MHz (government UHF)
- `★ 800 MHz` = 45 MHz offset
- `★ 700 MHz` = 30 MHz offset
- `★ Ham VHF` = 0.6 MHz
- VHF High (150-174 MHz) = anything goes, no standard offset!
- Cross-band links show 200+ MHz offset (UHF input → VHF output)

---

## Updating the Databases

### Update Private Land Mobile (FCC releases weekly)

```bash
# Download: https://data.fcc.gov/download/pub/uls/complete/a_LMpriv.zip
unzip ~/Downloads/a_LMpriv.zip -d ~/fcc-scanner/data/
cd ~/fcc-scanner
python3 import_fcc.py
python3 reload_fr.py
python3 add_em.py
```

### Update Amateur Radio Callsigns (update whenever you want)

```bash
# Download: https://data.fcc.gov/download/pub/uls/complete/a_amat.zip
unzip -o ~/Downloads/a_amat.zip -d ~/fcc-scanner/amateur/
cd ~/fcc-scanner
python3 import_amateur.py
```

### Update GMRS Radio Callsigns (update whenever you want)

```bash
# Download: https://data.fcc.gov/download/pub/uls/complete/l_gmrs.zip
unzip -o ~/Downloads/l_gmrs.zip -d ~/fcc-scanner/gmrs/
cd ~/fcc-scanner
python3 import_gmrs.py
```

### Never Need to Update
- `add_cities.py` / `uscities.csv` — city coordinates don't change
- `build_reference.py` / `fcc_reference.db` — FCC codes don't change

---

## Saved Reports

All saved searches go to `~/fcc-scanner/reports/` with timestamps:
```
results_WA_Asotin_20260318_143022.txt
results_freq_150.0-174.0_Lewiston_20260318_160512.txt
repeaters_Clarkston_WA_within_5_0_miles_20260320_154835.txt
results_frn_0001578236_20260321_111330.txt
```

Timestamp format is `YYYYMMDD_HHMMSS` — files sort chronologically.
Run the same search after a database update to see what changed!!

---

## Database Stats (as of March 2026 build)

| Database | Table | Records | Description |
|----------|-------|---------|-------------|
| fcc.db | hd | 2,827,785 | Part 90 license headers |
| fcc.db | en | 5,077,667 | Licensee/entity names |
| fcc.db | lo | 1,347,539 | Transmitter locations with GPS |
| fcc.db | fr | 5,185,935 | Frequency assignments |
| fcc.db | em | 10,446,808 | Emission designators |
| fcc.db | cities | 31,257 | US cities for offline lookup |
| fcc.db | amateur | 3,346,184 | Ham radio callsigns |
| fcc.db | gmrs | 578,933 | GMRS radio callsigns |
| fcc_reference.db | emission_lookup | 63+ | Emission designator decoder |
| fcc_reference.db | station_class | 36+ | Station class decoder |

**Total records: over 30 million — all offline, all instant!!**

---

## Backing Up This Project

```bash
cp ~/fcc-scanner/*.py ~/your-backup-location/
cp ~/fcc-scanner/uscities.csv ~/your-backup-location/
cp ~/fcc-scanner/fcc_reference.db ~/your-backup-location/
```

**Do NOT need to back up:**
- `fcc.db` — rebuilt from FCC downloads any time (~25 min)
- `data/*.dat` — re-downloaded from FCC
- `amateur/*.dat` — re-downloaded from FCC
- `gmrs/*.dat` — re-downloaded from FCC

**GitHub:** https://github.com/KJ7TNY/fcc-uls-scanner

---

## Troubleshooting

**"Database not found"**
→ Run import_fcc.py first

**"Reference DB: ✗"**
→ Run build_reference.py

**HamCall won't start — ModuleNotFoundError tkinter**
→ Run: `sudo apt install python3-tk`

**"City not found"**
→ Try a nearby larger city, or use option 2 (coordinates)

**Search returns 0 results on a frequency you know exists**
→ The FCC doesn't require GPS coordinates — some licenses have none
→ Use option 3 (call sign) or option 8 (FRN) to find it directly
→ This is an FCC data gap, not a bug in this tool

**HamCall shows wrong license class**
→ Re-download a_amat.zip and run import_amateur.py
→ Blank AM.dat record = General class

**FCC download URL broken**
→ Search "FCC ULS complete database download private land mobile"
→ Look for current URL at data.fcc.gov

---

## Tips & Tricks

- **Single frequency search:** In option 6, press ENTER on high frequency
  to search for one exact frequency — no range needed!

- **FRN is the power tool:** Every result shows an FRN — use option 8
  to find ALL transmitters for that entity across ALL their call signs!!

- **Cross-reference with scanner:** Hear a mystery frequency?
  Option 6 single frequency lookup identifies who it is instantly!!

- **Coordinate trick:** Copy coords from any result and paste into
  option 2 to search around that exact tower location

- **Cross-band links:** Repeater offset of 200+ MHz means it receives
  on one band and retransmits on another — common in canyon country

- **FRN reveals hidden systems:** One agency can have 8+ call signs
  under one FRN — option 8 reveals the FULL radio infrastructure!!

- **FX2 = cross-band input:** If you see FX2 in results it's a
  secondary input — probably receiving on a different band

- **Missing GPS locations:** Some FCC licenses have transmitters visible
  on the FCC website but no coordinates in the download — FCC data gap,
  use call sign or FRN search to find them

- **Two tools, one jailhouse:** search_fcc.py for deep Part 90 research,
  hamcall.py for quick ham & gmrs ID — both read the same fcc.db database!!

---

*Built March 2026 — Linux Mint — Python 3.12 — SQLite*
*"I Will Find You" 📻🚀*
*— Minty & The Wizard 🧙‍♂️*
