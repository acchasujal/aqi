# EXP-025-WEATHER input audit — 8 November 2026

Initial raw audit saved before application code changes. Original-source provenance is
in INPUT_PROVENANCE.json; complete per-message decoder output is in the two
`*.audit.json` files. These supersede the different filenames/hashes in the request.

| Input | Bytes | Edition | Messages | Run UTC | Actual contents |
|---|---:|---:|---:|---|---|
| f65626933fa022c9da340289d7db86e7.grib | 113256 | 1 | 605 | 2026-11-08 00:00 | Five fields at every lead 0–120; surface pressure absent |
| gfs.t06z.pgrb2.0p25.f061 | 1564 | 2 | 8 | 2026-11-08 06:00 | Lead61; six intended combinations plus surface TMP and interval-average PRATE |

CAMS SHA256: `63cee70731bef9368b024aa8d629dfb61787af45483e952e41b8349cc27e2abf`.
GFS SHA256: `07379d81726f0c0f258f43f05c31cd6390f932b053d171e01023b1b5fdfb3016`.
Both were copied unchanged into ignored `data/external/weather/incoming/`.
Neither supplied file is the partial two-lead CAMS or all-variable f013 described
in the pasted request. Those older originals were not located or overwritten.

CAMS: 6×6 regular latitude/longitude, 18–20N/72–74E, 0.4 degrees,
north-to-south scanning. Parameters 128:165/166/167/168 and 210:73,
surface level0; native units m s**-1, K, kg m**-3. All 36 values per message
are finite; no bitmap/missing values. Private leads67–114 are complete for
five variables (240 messages), but all 48 surface-pressure records are absent.
The strict six-field ingestion gate therefore fails. No need to redownload
those five fields. PM2.5 conversion is multiplication by 1e9.

GFS: 4×4 regular grid, 18.75–19.50N/72.50–73.25E, 0.25 degrees,
south-to-north scanning; all16 values/message finite, no bitmap.
Valid time is 10 November19:00 UTC. Instant PRATE (template0) and average
PRATE (template8, leads60–61) are distinct. Surface TMP must not substitute
for 2m TMP. HPBL 0/3/196 is decoded numerically but ecCodes2.50.0 labels
its name/units unknown; any resolution requires an explicit NCEP table reference.
Only one of48 required hourly files is supplied. All four station coordinates
from Stations.csv lie within both grid extents; interpolation is checked separately.

The per-message JSON includes identifiers, templates, levels, units, clocks,
scan orientation, grid extent, bitmap, packing and decoded min/max/mean/count.
GRIB1's decoder-reported template0 is a derived accessor, not a GRIB2 template.
Original download URLs, request payloads, retrieval times and publication evidence
were not supplied. Local preservation time is explicitly distinct from retrieval.

## Decoder environment

Native runtime: CPython3.12.10 Windows ARM64. No ecCodes/cfgrib/pygrib,
grib_ls/grib_dump/wgrib2 or installed WSL found. Tested official ecCodes2.50.0
win_amd64 wheel with official Python3.12.10 embedded amd64 under Windows
emulation. It successfully decoded every message of both files. Runtime/wheels
are isolated under ignored `data/processed/weather_tools/`; ML venv unchanged.
No handcrafted binary-value decoder is used. Reproduction details will accompany
the committed audit CLI. The initial one-off audit is preserved locally there.
