import requests
import json
import os
from datetime import datetime, timedelta

SENSOR_ID = "94448"
URL = f"https://data.sensor.community/airrohr/v1/sensor/{SENSOR_ID}/"
base_dir = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(base_dir, "..", "data", "sensor_history.json")

def update_data():
    # 1. Get new data from API
    try:
        response = requests.get(URL, timeout=10)
        new_entries = response.json()
    except Exception as e:
        print(f"Error fetching data: {e}")
        return
    
    # 2. Load existing history
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            try:
                history = json.load(f)
            except:
                history = []
    else:
        history = []

    # 3. Merge new entries (avoiding duplicates)
    existing_timestamps = {entry['timestamp'] for entry in history}
    
    for entry in new_entries:
        if entry['timestamp'] not in existing_timestamps:
            flat_entry = {
                "timestamp": entry['timestamp'],
                "values": {item['value_type']: item['value'] for item in entry['sensordatavalues']}
            }
            history.append(flat_entry)

    # 4. PRUNING: Remove entries older than 24 hours
    # The API uses UTC time format: "YYYY-MM-DD HH:MM:SS"
    now_utc = datetime.utcnow()
    cutoff = now_utc - timedelta(hours=24)
    
    # Filter the list: only keep items where the timestamp is after the cutoff
    pruned_history = [
        entry for entry in history 
        if datetime.strptime(entry['timestamp'], "%Y-%m-%d %H:%M:%S") > cutoff
    ]

    # 5. SORT (Ensure perfect time sequence)
    # This sorts everything from oldest at the top to newest at the bottom
    pruned_history.sort(key=lambda x: x['timestamp'])

    # 6. Save back to file
    with open(DATA_FILE, "w") as f:
        json.dump(pruned_history, f, indent=2)
    
    print(f"Update complete. Points in history: {len(pruned_history)}")

if __name__ == "__main__":
    update_data()
