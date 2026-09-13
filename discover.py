import os
import requests

API_KEY = os.environ["RIDB_API_KEY"]

url = "https://ridb.recreation.gov/api/v1/facilities"

params = {
    "query": "Mammoth Cave",
    "limit": 10
}

headers = {
    "apikey": API_KEY
}

response = requests.get(url, params=params, headers=headers, timeout=20)
response.raise_for_status()

data = response.json()

print("RIDB search results for: Mammoth Cave")
print()

for facility in data.get("RECDATA", []):
    print(
        facility.get("FacilityName"),
        "| ID:",
        facility.get("FacilityID")
    )
