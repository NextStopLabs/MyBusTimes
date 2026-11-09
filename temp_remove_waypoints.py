import json
from pathlib import Path

src = Path(__file__).with_name("temp.json")

with src.open() as f:
    data = json.load(f)

cleaned = [entry for entry in data if not entry.get("waypoint")]

with src.open("w") as f:
    json.dump(cleaned, f, indent=4)

print(f"Removed {len(data) - len(cleaned)} waypoints, {len(cleaned)} stops left.")
