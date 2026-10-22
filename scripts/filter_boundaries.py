"""Filter the national Spain provinces boundary file into per-region GeoJSONs.

Mirrors filter_edistribucion.py's per-region split, so the boundary
files live next to the substation CSVs they'll be plotted with.

Uses the official IGN WFS extract (fetch_ign_boundaries.py), not the
community-sourced spain_provinces.geojson.
"""
import json
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_PATH = PROJECT_DIR / "data" / "gis" / "raw" / "boundaries" / "spain_provinces_ign.geojson"
CLEAN_DIR = PROJECT_DIR / "data" / "gis" / "clean"

REGIONS = {
    "catalunya": ["Barcelona", "Girona", "Lleida", "Tarragona"],
}


def main() -> None:
    data = json.loads(RAW_PATH.read_text(encoding="utf-8"))

    for region_key, province_names in REGIONS.items():
        features = [
            f for f in data["features"]
            if f["properties"].get("name") in province_names
        ]
        out = {"type": "FeatureCollection", "features": features}

        CLEAN_DIR.mkdir(parents=True, exist_ok=True)
        out_path = CLEAN_DIR / f"boundary_{region_key}.geojson"
        out_path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
        print(f"{region_key}: {len(features)} provinces -> {out_path}")


if __name__ == "__main__":
    main()
