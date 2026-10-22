"""Fetch 220/400 kV substations from OpenStreetMap via the Overpass API.

REE's capacity files list transmission nodes by name only, with no
coordinates. OSM is the only open source found so far that has those
substations with a name and a location, so this pulls every substation
tagged with a 220 kV or 400 kV voltage inside each region's bounding box.

Bounding boxes include some of the neighbouring regions; matching to REE
nodes (scripts/classify_substations.py) is what decides which ones are used.
OSM is community-mapped: names and completeness are not guaranteed.
"""
import json
import time
from pathlib import Path

import requests

PROJECT_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_DIR / "data" / "gis" / "raw" / "osm_subestaciones"

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "datadriven-course-project/0.1"

# (south, west, north, east)
REGION_BBOXES = {
    "catalunya": (40.50, 0.15, 42.87, 3.34),
}

QUERY = """[out:json][timeout:120];
(nwr["power"="substation"]["voltage"~"(^|;)(220000|400000)(;|$)"]({s},{w},{n},{e}););
out tags center;"""


def fetch(bbox: tuple[float, float, float, float]) -> dict:
    s, w, n, e = bbox
    query = QUERY.format(s=s, w=w, n=n, e=e)
    # the public Overpass server often answers 502/504 under load: retry with backoff
    for attempt in range(6):
        resp = requests.post(
            OVERPASS_URL, data={"data": query}, headers={"User-Agent": USER_AGENT}, timeout=200
        )
        if resp.status_code == 200:
            return resp.json()
        time.sleep(15 * (attempt + 1))
    resp.raise_for_status()


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for region, bbox in REGION_BBOXES.items():
        data = fetch(bbox)
        out_path = OUT_DIR / f"{region}_220_400kv.json"
        out_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        print(f"{region}: {len(data['elements'])} substations -> {out_path}")


if __name__ == "__main__":
    main()
