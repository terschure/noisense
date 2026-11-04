#!/usr/bin/env python3
"""
Split a noise-sensor CSV into one JSON file per Amsterdam calendar day.

Input : CSV whose timestamps are in AMSTERDAM local time (default; see --csv-tz)
Output: JSON files whose timestamps are in UTC, like the Sensor.community API

Each file holds one Amsterdam day (00:00-23:59 local). Because the timestamps
inside are UTC, a file for a summer day runs from 22:00 UTC (the evening
before) to 21:59 UTC; in winter from 23:00 UTC to 22:59 UTC.

Usage:
    python csv_to_daily_json.py geluidniveaus_93081.csv
    python csv_to_daily_json.py input.csv --sensor 93081 --out data
    python csv_to_daily_json.py input.csv --csv-tz UTC      # if a CSV is in UTC

Files are named sensor<ID>_<YYYY-MM-DD>.json (Amsterdam date). A
manifest.json with the list of file names is written as well.

Expected CSV columns (semicolon separated, order matters):
    DateTime ; Leq ; Lamax ; Lamin
"""

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
    AMS = ZoneInfo("Europe/Amsterdam")
except Exception:  # missing tz database (common on Windows)
    sys.exit("Time zone data not found. Run: pip install tzdata")

TS_FORMAT = "%Y-%m-%d %H:%M:%S"


def detect_sensor_id(header):
    """Pull the sensor number out of a header like 'Leq GLD_SeCo_93081'."""
    for col in header[1:]:
        m = re.search(r"(\d{4,})", col)
        if m:
            return m.group(1)
    return None


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter=";")
        header = next(reader)
        rows = []
        for n, row in enumerate(reader, start=2):
            if not row or not any(c.strip() for c in row):
                continue
            try:
                ts = row[0].strip().strip('"')
                naive = datetime.strptime(ts, TS_FORMAT)
                leq, lamax, lamin = (float(c.replace(",", ".")) for c in row[1:4])
            except (ValueError, IndexError):
                print(f"  skipped line {n}: {row}", file=sys.stderr)
                continue
            rows.append((naive, leq, lamax, lamin))
    return header, rows


def to_utc_series(naive_times, tz):
    """
    Convert naive local datetimes (in file order) to UTC.

    When the clocks go back (last Sunday of October) the local times
    02:00-02:59 occur twice. The file is chronological, so when a local time
    is ambiguous we take the first occurrence, unless that would put the
    reading before the previous one - then it must be the second occurrence.
    """
    out, prev = [], None
    for naive in naive_times:
        first = naive.replace(tzinfo=tz, fold=0).astimezone(timezone.utc)
        second = naive.replace(tzinfo=tz, fold=1).astimezone(timezone.utc)
        utc = first
        if first != second and prev is not None and first < prev:
            utc = second
        out.append(utc)
        prev = utc
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", help="input CSV file")
    ap.add_argument("--sensor", help="sensor ID for the file names (default: taken from CSV header)")
    ap.add_argument("--out", default="out", help="output folder (default: ./out)")
    ap.add_argument("--csv-tz", default="Europe/Amsterdam",
                    help="time zone of the CSV timestamps (default: Europe/Amsterdam; use UTC if the CSV is in UTC)")
    args = ap.parse_args()

    csv_tz = timezone.utc if args.csv_tz.upper() == "UTC" else ZoneInfo(args.csv_tz)

    header, rows = read_csv(args.csv)
    if not rows:
        sys.exit("No valid rows found.")

    sensor = args.sensor or detect_sensor_id(header)
    if not sensor:
        sys.exit("Could not detect the sensor ID; pass it with --sensor.")

    # Keep file order for the DST disambiguation, but require it to be chronological
    utc_times = to_utc_series([r[0] for r in rows], csv_tz)
    if any(b < a for a, b in zip(utc_times, utc_times[1:])):
        print("warning: CSV is not in chronological order; sorting by UTC time", file=sys.stderr)

    records = sorted(zip(utc_times, rows), key=lambda x: x[0])

    # Group by Amsterdam date; drop duplicate timestamps
    days, seen, dupes = defaultdict(list), set(), 0
    for utc, (_, leq, lamax, lamin) in records:
        if utc in seen:
            dupes += 1
            continue
        seen.add(utc)
        day = utc.astimezone(AMS).strftime("%Y-%m-%d")
        days[day].append({
            "timestamp": utc.strftime(TS_FORMAT),             # UTC
            "values": {
                "noise_LAeq":   f"{leq:.2f}",
                "noise_LA_min": f"{lamin:.2f}",
                "noise_LA_max": f"{lamax:.2f}",
            },
        })

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    stems = []
    for day in sorted(days):
        stem = f"sensor{sensor}_{day}"
        with open(out / f"{stem}.json", "w", encoding="utf-8") as f:
            json.dump(days[day], f, indent=2)
        stems.append(stem)
        first, last = days[day][0]["timestamp"], days[day][-1]["timestamp"]
        print(f"{stem}.json  {len(days[day]):4d} readings  {first} -> {last} (UTC)")

    with open(out / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(stems, f, indent=2)

    print(f"\n{len(records) - dupes} readings in {len(stems)} files -> {out.resolve()}")
    if dupes:
        print(f"{dupes} duplicate timestamps ignored")


if __name__ == "__main__":
    main()
