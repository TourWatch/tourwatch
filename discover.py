import os
import requests

API_KEY = os.environ["RIDB_API_KEY"]
HEADERS = {"apikey": API_KEY}
BASE = "https://ridb.recreation.gov/api/v1"

search_term = "Mammoth Cave"

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

# For this test, automatically find the Mammoth Cave tour facility.
target = next(
    (
        facility for facility in facilities
        if "MAMMOTH CAVE NATIONAL PARK TOURS"
        in facility.get("FacilityName", "").upper()
    ),
    None
)

if not target:
    raise RuntimeError("Could not find Mammoth Cave tour facility")

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
