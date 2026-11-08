# Tested decoder and reproduction

Native ML Python is3.12.10 ARM64 on Windows11. It remains unchanged. No installed
WSL or GRIB command-line decoder was found. Official ecCodes2.50.0 win_amd64
successfully runs under Windows x64 emulation using official portable CPython.
No native ARM64 compatibility is claimed. Provisioning initially failed in the
network-restricted shell; approved network execution downloaded the tools.

Download the official embedded archive
[Python3.12.10 amd64](https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip)
into ignored `data/processed/weather_tools/`, extract to `python_x64/`, and download
compatible wheels (the exact installed wheel hashes are in DECODER_WHEEL_HASHES.json):

```powershell
.venv\Scripts\python.exe -m pip download --only-binary=:all: --platform win_amd64 --python-version 312 --implementation cp --abi cp312 eccodes==2.50.0 --dest data/processed/weather_tools/wheels --disable-pip-version-check
```

Extract the six wheels into `python_x64/packages/`. Set `python312._pth` to four
lines: `python312.zip`, `.`, `packages`, `import site`. This isolates the tools
from the native ML environment. Versions fetched: ecCodes2.50.0, numpy2.5.4,
cffi2.1.1, attrs26.1.0, findlibs0.1.5, pycparser3.12. Official binding documentation:
[ECMWF ecCodes Python](https://github.com/ecmwf/eccodes-python).

```powershell
data\processed\weather_tools\python_x64\python.exe -c "import eccodes; print(eccodes.codes_get_api_version())"
data\processed\weather_tools\python_x64\python.exe scripts/weather_pipeline.py audit data/external/weather/incoming/f65626933fa022c9da340289d7db86e7.grib --output data/processed/weather_tools/cams_decoded.json --include-grid
data\processed\weather_tools\python_x64\python.exe scripts/weather_pipeline.py gfs --date 2026-11-08 --cycle 6 --first 61 --last 108 --output data/external/weather/noaa_gfs/20261108_06Z
$weatherGribs = Get-ChildItem data/external/weather/noaa_gfs/20261108_06Z -Filter 'gfs_20261108_06Z_f*_mumbai.grib2' | Sort-Object Name | ForEach-Object { Resolve-Path -Relative $_.FullName }
data\processed\weather_tools\python_x64\python.exe scripts/weather_pipeline.py decode-block --source gfs --input $weatherGribs --date 20261108 --cycle 6 --first 61 --last 108 --output data/processed/weather_tools/gfs_block_decoded.json
```

Audit/decoded output paths are exclusive: choose fresh names on reruns. GFS raw
downloads skip only matching hash/request receipts and are redecoded before reuse.
Framing checks use WMO message signature/declared-length/end-marker fields only;
all meteorological values and coordinates come from ecCodes. No unverified offset
decoder exists. HTML errors cannot become accepted raw files. Publication uses
an atomic exclusive hard link on the same filesystem; stale partials fail closed.

CAMS downloader is implemented but NOT authenticated/tested here. Its optional
`cdsapi>=0.7.7` dependency was not installed, no token was sought, and no provider
terms were accepted automatically. See ADS official setup and the exact request
JSON files. Current partial source can be analysed without another CAMS download.
