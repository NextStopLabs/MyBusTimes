import json

# Load the old-style JSON
with open("Bathwick.json", "r", encoding="utf-8") as infile:
    old_data = json.load(infile)

new_data = []

# Convert each old route to the new format
for route in old_data:
    new_route = {
        "Route Num": str(route["Route Num"]),  # Ensure all route numbers are strings
        "Inbound": {
            "In Dest": route["In Dest"],
            "Out Dest": route["Out Dest"]
        },
        "Outbound": {
            "In Dest": route["Out Dest"],
            "Out Dest": route["In Dest"]
        }
    }
    new_data.append(new_route)

# Save the new-style JSON
with open("new_routes.json", "w", encoding="utf-8") as outfile:
    json.dump(new_data, outfile, indent=2)
