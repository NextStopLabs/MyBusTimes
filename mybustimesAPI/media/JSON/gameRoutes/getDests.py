import requests
import json
import os

# API URL
url = "https://new.mybustimes.cc/api/game/Bathwick/"

# Send a GET request to the API
response = requests.get(url)

# Check if the response is successful
if response.status_code == 200:
    # Load the JSON data from the response
    data = response.json()

    # Initialize a set to hold unique destinations
    unique_destinations = set()

    # Iterate through each route in the data
    for route in data:
        # Add destinations from inbound and outbound details
        unique_destinations.add(route['Inbound']['In Dest'])
        unique_destinations.add(route['Inbound']['Out Dest'])
        unique_destinations.add(route['Outbound']['In Dest'])
        unique_destinations.add(route['Outbound']['Out Dest'])

    # Convert the set to a list
    unique_dest_list = list(unique_destinations)

    # Ensure the directory exists
    os.makedirs("Dests", exist_ok=True)

    # Save the unique destinations to a JSON file
    with open("Dests/Bathwick.json", "w") as file:
        json.dump(unique_dest_list, file, indent=4)

    print("Unique destinations have been saved to /Dests/Bathwick.json")

else:
    print(f"Failed to fetch data. Status code: {response.status_code}")
