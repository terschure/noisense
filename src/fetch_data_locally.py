"""
fetch_data.py — fetches your sensor API and appends the reading to a local
JSON file for today. Each day gets its own file: data/<YYYY-MM-DD>.json

HOW TO CONFIGURE:
  1. Fill in SENSOR_API_URL below (already set for your sensor ID).
  2. Point index.html at the data/ folder (e.g. fetch data/2026-03-09.json).
  3. Run once manually to test: python fetch_data_locally.py
  4. Run setup_scheduler.bat (as Administrator) to register the 5-min task.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

# ── Configuration ────────────────────────────────────────────────────────────

SENSOR_ID = "93081"
SENSOR_API_URL = f"https://data.sensor.community/airrohr/v1/sensor/{SENSOR_ID}/"

# The sensor.community API returns timestamps in UTC. This is used to convert
# them to local time. Using a real IANA timezone (rather than a fixed UTC+2
# offset) means it automatically switches between CET (UTC+1, winter) and
# CEST (UTC+2, summer/DST) on the correct dates each year.
LOCAL_TZ = ZoneInfo("Europe/Amsterdam")

# Local folder where daily files are saved (created automatically)
ARCHIVE_DIR = Path(__file__).parent / "data"

READINGS_PER_FETCH = 2  # adjust to what you observe
FETCHES_PER_DAY = 288   # 24h × 12 fetches/hour (every 5 min)
MAX_POINTS_PER_DAY = FETCHES_PER_DAY * READINGS_PER_FETCH  # safety cap per day

# ── Helpers ──────────────────────────────────────────────────────────────────

def parse_readings(response: list) -> list:
    """
    Parse ALL individual readings from the sensor.community API response.

    The API returns a list of readings from the last 5 minutes. Each has a
    timestamp and a sensordatavalues array. Returns them sorted chronologically,
    in the format:
      {"timestamp": "2026-03-09 22:27:18", "values": {"noise_LAeq": "46.19", ...}}
    Values are kept as strings to match the API output exactly.
    """
    records = []
    for reading in response:
        values = {
            item["value_type"]: item["value"]
            for item in reading["sensordatavalues"]
        }
        if not all(k in values for k in ("noise_LAeq", "noise_LA_min", "noise_LA_max")):
            continue

        # API timestamps are UTC; convert to local time (UTC+2)
        utc_dt = datetime.strptime(reading["timestamp"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        local_dt = utc_dt.astimezone(LOCAL_TZ)
        local_timestamp = local_dt.strftime("%Y-%m-%d %H:%M:%S")

        records.append({
            "timestamp": local_timestamp,
            "values": {
                "noise_LAeq":   values["noise_LAeq"],
                "noise_LA_min": values["noise_LA_min"],
                "noise_LA_max": values["noise_LA_max"],
            }
        })
    records.sort(key=lambda r: r["timestamp"])
    return records


def day_file_path(date_str: str) -> Path:
    """Return the path for a given day's data file (e.g. data/2026-03-09.json)."""
    ARCHIVE_DIR.mkdir(exist_ok=True)
    return ARCHIVE_DIR / f"{date_str}.json"


def load_day(path: Path) -> list:
    """Load a day's history from disk, or return an empty list if it doesn't exist yet."""
    if not path.exists():
        return []
    with open(path, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            print(f"  Warning: {path} was empty or corrupt, starting fresh")
            return []


def save_day(path: Path, history: list) -> None:
    """Write a day's history list back to disk."""
    with open(path, "w") as f:
        json.dump(history, f, indent=2)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    now_local = datetime.now(LOCAL_TZ)
    today_str = now_local.strftime("%Y-%m-%d")
    path = day_file_path(today_str)

    # 1. Fetch all readings from the last 5 minutes
    print("Fetching sensor data...")
    sensor_resp = requests.get(SENSOR_API_URL, timeout=10)
    sensor_resp.raise_for_status()
    new_records = parse_readings(sensor_resp.json())
    print(f"  Got {len(new_records)} new readings from API")

    # 2. Load today's existing data (empty list if this is a new day / new file)
    history = load_day(path)

    # 3. Merge: add only records whose timestamp is not already in history
    existing_timestamps = {r["timestamp"] for r in history}
    added = [r for r in new_records if r["timestamp"] not in existing_timestamps]
    print(f"  Adding {len(added)} new records (skipping {len(new_records) - len(added)} duplicates)")

    history.extend(added)
    history.sort(key=lambda r: r["timestamp"])  # keep chronological order
    history = history[-MAX_POINTS_PER_DAY:]      # safety cap, shouldn't normally trigger

    # 4. Write back to today's file
    print(f"Writing {len(history)} records to {path}...")
    save_day(path, history)
    print("Done ✓")


if __name__ == "__main__":
    main()
