import os
import requests

API_KEY = os.environ["RIDB_API_KEY"]
HEADERS = {"apikey": API_KEY}
BASE = "https://ridb.recreation.gov/api/v1"

search_term = os.getenv("SEARCH_TERM", "Mammoth Cave").strip() or "Mammoth Cave"

# Search for facilities
response = requests.get(
    f"{BASE}/facilities",
    params={"query": search_term, "limit": 50},
    headers=HEADERS,
    timeout=20
)
response.raise_for_status()
facilities = response.json().get("RECDATA", [])

print(f"RIDB search results for: {search_term}\n")

for facility in facilities:
    print(f"{facility.get('FacilityName')} | ID: {facility.get('FacilityID')}")

# Select the top RIDB search result for this test.
target = facilities[0] if facilities else None

if not target:
    raise RuntimeError(f"No facilities found for: {search_term}")

facility_id = target["FacilityID"]

print()
print(f"SELECTED: {target['FacilityName']} | ID: {facility_id}")
print()
print("Tours attached to this facility:")

# Ask RIDB which tours belong to the selected facility.
response = requests.get(
    f"{BASE}/facilities/{facility_id}/tours",
    headers=HEADERS,
    timeout=20
)
response.raise_for_status()

tours = response.json().get("RECDATA", [])

for tour in tours:
    print(
        f"{tour.get('TourName')} | "
        f"Tour ID: {tour.get('TourID')}"
    )

print()
print(f"Found {len(tours)} tours.")
