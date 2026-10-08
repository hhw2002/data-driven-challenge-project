"""Fetch official province boundaries from IGN's INSPIRE Administrative Units WFS.

Replaces the community-sourced spain_provinces.geojson (data/raw/boundaries/)
with the authoritative source: https://www.ign.es/wfs-inspire/unidades-administrativas
(au:AdministrativeUnit feature type, nationalLevelName == 'Provincia').

The service is a GeoServer app-schema (complex features) WFS: CQL_FILTER on
nested properties is unreliable server-side (tested — combining name + level
in one filter times out, and filtering on level alone returns some unrelated
lower-level units mixed in). So this fetches a batch filtered loosely by
level and does the exact name match client-side instead.
"""
import re
from pathlib import Path

import requests

PROJECT_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_DIR / "data" / "raw" / "boundaries"

WFS_URL = "https://www.ign.es/wfs-inspire/unidades-administrativas"

TARGET_PROVINCES = [
    "Huesca", "Teruel", "Zaragoza",  # Aragón
    "Barcelona", "Girona", "Lleida", "Tarragona",  # Catalunya
]

NS = {
    "wfs": "http://www.opengis.net/wfs/2.0",
    "au": "http://inspire.ec.europa.eu/schemas/au/4.0",
    "gml": "http://www.opengis.net/gml/3.2",
    "gn": "http://inspire.ec.europa.eu/schemas/gn/4.0",
    "gmd": "http://www.isotc211.org/2005/gmd",
}


def fetch_raw_xml() -> str:
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": "au:AdministrativeUnit",
        "CQL_FILTER": "nationalLevelName='Provincia'",
        "count": 100,
    }
    resp = requests.get(WFS_URL, params=params, timeout=120)
    resp.raise_for_status()
    return resp.text


def parse_features(xml_text: str):
    """Yield (name, level, list_of_rings) for each au:AdministrativeUnit member.

    Regex-based on purpose: this WFS's GML uses inlined geometry comments and
    namespace prefixes that make ElementTree's iterparse awkward here; each
    <wfs:member> block is self-contained, so splitting on that tag and
    regexing within each block is simpler and good enough for a one-off pull.
    """
    members = re.findall(r"<wfs:member>.*?</wfs:member>", xml_text, re.S)
    for member in members:
        name_match = re.search(r"<gn:text>(.*?)</gn:text>", member)
        level_match = re.search(
            r"<au:nationalLevelName>\s*<gmd:LocalisedCharacterString[^>]*>(.*?)</gmd:LocalisedCharacterString>",
            member, re.S,
        )
        if not name_match or not level_match:
            continue
        name = name_match.group(1)
        level = level_match.group(1)
        rings = []
        for poslist in re.findall(r"<gml:posList[^>]*>(.*?)</gml:posList>", member, re.S):
            coords = [float(v) for v in poslist.split()]
            # posList is lat lon lat lon ... (EPSG:4258/4326 axis order) -> GeoJSON wants [lon, lat]
            ring = [[coords[i + 1], coords[i]] for i in range(0, len(coords), 2)]
            rings.append(ring)
        yield name, level, rings


def main() -> None:
    xml_text = fetch_raw_xml()

    features = []
    seen = set()
    for name, level, rings in parse_features(xml_text):
        if level != "Provincia" or name not in TARGET_PROVINCES or name in seen:
            continue
        seen.add(name)
        features.append({
            "type": "Feature",
            "properties": {"name": name},
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [[ring] for ring in rings],
            },
        })

    missing = set(TARGET_PROVINCES) - seen
    if missing:
        print(f"WARNING: missing provinces (not found in this batch): {missing}")

    geojson = {"type": "FeatureCollection", "features": features}

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "spain_provinces_ign.geojson"
    import json
    out_path.write_text(json.dumps(geojson, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(features)} provinces -> {out_path}")


if __name__ == "__main__":
    main()
