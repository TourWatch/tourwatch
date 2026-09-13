#!/usr/bin/env python3
"""TourWatch proof-of-concept monitor.

Read-only checker for Recreation.gov timed-entry/tour availability.
It does not reserve, book, authenticate, or bypass any access controls.
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

import requests

BASE_URL = "https://www.recreation.gov"
CONFIG_PATH = Path("watches.json")
TIMEOUT_SECONDS = 20


def daterange(start: str, end: str) -> Iterable[str]:
    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)
    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")
    current = start_date
    while current <= end_date:
        yield current.isoformat()
        current += timedelta(days=1)


def get_any_count(value: Any) -> int:
    if isinstance(value, dict):
        for key in ("ANY", "FIT", "COMM", "WALKUP", "LOTTERY"):
            if key in value and isinstance(value[key], (int, float)):
                return int(value[key])
    if isinstance(value, (int, float)):
        return int(value)
    return 0


def extract_slots(payload: Any) -> list[dict[str, Any]]:
    """Normalize the common Recreation.gov timed-entry response shapes."""
    if isinstance(payload, list):
        raw_slots = payload
    elif isinstance(payload, dict):
        # Keep this forgiving because the public web app's JSON shape can evolve.
        for key in ("availability", "slots", "tour_availability", "data"):
            if isinstance(payload.get(key), list):
                raw_slots = payload[key]
                break
        else:
            # Some responses are dictionaries keyed by tour/time identifier.
            candidates = [v for v in payload.values() if isinstance(v, dict)]
            raw_slots = candidates
    else:
        raw_slots = []

    normalized: list[dict[str, Any]] = []
    for slot in raw_slots:
        if not isinstance(slot, dict):
            continue
        inventory = get_any_count(slot.get("inventory_count"))
        reserved = get_any_count(slot.get("reservation_count"))
        available = max(inventory - reserved, 0)
        tour_id = slot.get("tour_id") or slot.get("tourId") or slot.get("id")
        tour_name = (
            slot.get("tour_name")
            or slot.get("tourName")
            or slot.get("name")
            or slot.get("title")
            or "Unknown tour"
        )
        tour_time = (
            slot.get("tour_time")
            or slot.get("tourTime")
            or slot.get("time")
            or slot.get("start_time")
            or slot.get("startTime")
            or "Unknown time"
        )
        normalized.append(
            {
                "tour_id": str(tour_id) if tour_id is not None else "",
                "tour_name": str(tour_name),
                "tour_time": str(tour_time),
                "inventory": inventory,
                "reserved": reserved,
                "available": available,
                "raw": slot,
            }
        )
    return normalized


def check_date(session: requests.Session, facility_id: str, day: str) -> tuple[list[dict[str, Any]], Any]:
    # Mammoth Cave and other /ticket/facility resources use the ticket API.
    # Some timed-entry facilities use /api/timedentry instead, so try the
    # ticket endpoint first and fall back to timedentry if needed.
    endpoints = [
        f"{BASE_URL}/api/ticket/availability/facility/{facility_id}",
        f"{BASE_URL}/api/timedentry/availability/facility/{facility_id}",
    ]
    last_payload = None
    for url in endpoints:
        response = session.get(url, params={"date": day}, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
        last_payload = payload
        slots = extract_slots(payload)
        if slots:
            return slots, payload
        # An empty list often means this facility belongs to the other API family.
        if payload not in ([], {}, None):
            return slots, payload
    return [], last_payload


def main() -> int:
    if not CONFIG_PATH.exists():
        print(f"Missing {CONFIG_PATH}", file=sys.stderr)
        return 2

    config = json.loads(CONFIG_PATH.read_text())
    watches = config.get("watches", [])
    if not watches:
        print("No watches configured.")
        return 0

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "TourWatch/0.1 (+https://github.com/TourWatch/tourwatch; read-only availability checker)",
            "Accept": "application/json,text/plain,*/*",
        }
    )

    print(f"TourWatch check started: {datetime.now().astimezone().isoformat(timespec='seconds')}")
    found_any = False

    for watch in watches:
        name = watch.get("name", "Unnamed watch")
        facility_id = str(watch["facility_id"])
        party_size = int(watch.get("party_size", 1))
        start_date = watch["start_date"]
        end_date = watch.get("end_date", start_date)
        tour_name_contains = str(watch.get("tour_name_contains", "")).strip().lower()

        print(f"\n=== {name} ===")
        print(f"Facility {facility_id} | {start_date} to {end_date} | party size {party_size}")

        for day in daterange(start_date, end_date):
            try:
                slots, payload = check_date(session, facility_id, day)
            except requests.RequestException as exc:
                print(f"{day}: REQUEST FAILED: {exc}")
                continue
            except ValueError as exc:
                print(f"{day}: JSON/PARSE FAILED: {exc}")
                continue

            if not slots:
                # This line is intentional: on the first run it tells us whether
                # the endpoint works but our parser needs adjustment.
                payload_type = type(payload).__name__
                keys = list(payload.keys())[:12] if isinstance(payload, dict) else []
                print(f"{day}: endpoint responded, but no slots normalized (payload={payload_type}, keys={keys})")
                continue

            matching = []
            for slot in slots:
                haystack = f"{slot['tour_name']} {slot['tour_id']}".lower()
                if tour_name_contains and tour_name_contains not in haystack:
                    continue
                matching.append(slot)

            available = [s for s in matching if s["available"] >= party_size]
            if available:
                found_any = True
                print(f"{day}: AVAILABLE ({len(available)} matching slot(s))")
                for slot in available:
                    print(
                        f"  - {slot['tour_name']} | {slot['tour_time']} | "
                        f"available={slot['available']} | tour_id={slot['tour_id']}"
                    )
            else:
                print(f"{day}: no qualifying availability ({len(matching)} slot(s) checked)")

    print("\nResult:", "at least one qualifying opening found" if found_any else "no qualifying openings found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
