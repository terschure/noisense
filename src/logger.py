import requests
import json
import os
import subprocess
from datetime import datetime

SENSOR_ID = "93081"
URL = f"https://data.sensor.community/airrohr/v1/sensor/{SENSOR_ID}/"
base_dir = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(base_dir, "..", "data")

def git_push():
    # Use the full path to git.exe found via 'where git'
    git_path = r"C:/Program Files/Git/bin/git.exe" 
    try:
        # We also need to ensure we are in the right directory
        subprocess.run([git_path, "add", "data/*.json"], check=True, cwd=base_dir)
        msg = f"Auto-update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run([git_path, "commit", "-m", msg], check=True, cwd=base_dir)
        subprocess.run([git_path, "push"], check=True, cwd=base_dir)
        print("Successfully pushed to GitHub!")
    except Exception as e:
        with open(os.path.join(base_dir, "error_log.txt"), "a") as f:
            f.write(f"{datetime.now()}: Git push failed: {e}\n")

def update_data():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    try:
        response = requests.get(URL, timeout=10)
        new_entries = response.json()
    except Exception as e:
        print(f"Error fetching data: {e}")
        return
    
    grouped_data = {}
    for entry in new_entries:
        ts_str = entry['timestamp']
        date_key = ts_str.split(" ")[0]
        
        flat_entry = {
            "timestamp": ts_str,
            "values": {item['value_type']: item['value'] for item in entry['sensordatavalues']}
        }

        if date_key not in grouped_data:
            grouped_data[date_key] = []
        grouped_data[date_key].append(flat_entry)

    updated_files = False
    for date_key, entries in grouped_data.items():
        file_path = os.path.join(DATA_DIR, f"sensor{SENSOR_ID}_{date_key}.json")
        
        existing_data = []
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                try:
                    existing_data = json.load(f)
                except: existing_data = []

        existing_timestamps = {e['timestamp'] for e in existing_data}
        added_new = False
        for e in entries:
            if e['timestamp'] not in existing_timestamps:
                existing_data.append(e)
                added_new = True
                updated_files = True

        if added_new:
            existing_data.sort(key=lambda x: x['timestamp'])
            with open(file_path, "w") as f:
                json.dump(existing_data, f, indent=2)
            print(f"Updated {date_key}. Total points: {len(existing_data)}")

    # Only push if there was actually new data to upload
    if updated_files:
        git_push()
    else:
        print("No new data points found. Skipping push.")

if __name__ == "__main__":
    update_data()
