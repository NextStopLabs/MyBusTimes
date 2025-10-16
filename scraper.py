import requests
from bs4 import BeautifulSoup
import json

url = "https://bustimes.org/services/nma-tamworth-station-national-memorial-arboretum"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# Fetch the page
response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, "html.parser")

# Output dictionary
timetable_data = {}
stop_order = 0

# Find all grouping sections (each direction: e.g., Burton -> Lichfield and reverse)
groupings = soup.select("div.groupings div.grouping")

for grouping in groupings:
    direction = grouping.find("h2").text.strip()

    # Each direction might have its own table
    table = grouping.find("table", class_="timetable")
    if not table:
        continue

    rows = table.find_all("tr")
    for row in rows:
        stop_name_tag = row.find("th", class_="stop-name")
        if not stop_name_tag:
            continue

        stop_name = stop_name_tag.text.strip()
        timing_point = 'minor' not in row.get('class', [])
        times = [td.text.strip() for td in row.find_all("td") if td.text.strip()]

        # Build dictionary entry
        timetable_data[stop_name] = {
            "stopname": stop_name,
            "timing_point": timing_point,
            "times": times,
        }

# Output JSON
json_output = json.dumps(timetable_data, indent=2)
print(json_output)
