"""Fetch official power plant / substation geometry from IGN's BTN vector tiles.

Sweeps every z13 tile covering Aragon and Catalunya's bounding boxes,
decodes each one, and keeps only the two energy-infrastructure layers:
- btn0713s_cen_elec (centrales eléctricas / power plants)
- btn0719s_tra_elec (transformación eléctrica / substations)

This is a full regional sweep (~11.6k tile requests total), not a lookup
restricted to known e-distribución node coordinates — it also catches
generation plants that connect directly to the transmission grid (REE)
rather than through e-distribución's distribution network, which the
e-distribución capacity files (data/raw/edistribucion_capacidad/) don't
cover.

Tiles are cached to data/raw/ign_btn_energia/tile_cache/ so a re-run
after a partial failure doesn't re-download tiles already fetched.
"""
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import mapbox_vector_tile
import mercantile
import requests

PROJECT_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_DIR / "data" / "raw" / "ign_btn_energia"
CACHE_DIR = OUT_DIR / "tile_cache"

TILE_URL = "https://vt-btn.idee.es/1.0.0/btn/tile/{z}/{y}/{x}.pbf"
ZOOM = 13
EXTENT = 4096
LAYERS = ["btn0713s_cen_elec", "btn0719s_tra_elec"]

REGION_BBOXES = {
    "aragon": (-2.17, 39.85, 0.77, 42.92),
    "catalunya": (0.16, 40.52, 3.33, 42.86),
}

session = requests.Session()


def fetch_tile(tile: mercantile.Tile) -> bytes:
    cache_path = CACHE_DIR / f"{tile.z}_{tile.x}_{tile.y}.pbf"
    if cache_path.exists():
        return cache_path.read_bytes()
    url = TILE_URL.format(z=tile.z, y=tile.y, x=tile.x)
    for attempt in range(3):
        try:
            resp = session.get(url, timeout=20)
            if resp.status_code == 200:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_bytes(resp.content)
                return resp.content
            if resp.status_code == 204:
                return b""
        except requests.RequestException:
            time.sleep(0.5 * (attempt + 1))
    return b""


def tile_to_lonlat(px, py, bounds):
    lon = bounds.west + (px / EXTENT) * (bounds.east - bounds.west)
    lat = bounds.north - (py / EXTENT) * (bounds.north - bounds.south)
    return [lon, lat]


def convert_geometry(geom, bounds):
    def convert_ring(ring):
        return [tile_to_lonlat(px, py, bounds) for px, py in ring]

    gtype = geom["type"]
    coords = geom["coordinates"]
    if gtype == "Polygon":
        return {"type": "Polygon", "coordinates": [convert_ring(r) for r in coords]}
    if gtype == "MultiPolygon":
        return {"type": "MultiPolygon", "coordinates": [[convert_ring(r) for r in poly] for poly in coords]}
    if gtype == "Point":
        return {"type": "Point", "coordinates": tile_to_lonlat(coords[0], coords[1], bounds)}
    if gtype == "LineString":
        return {"type": "LineString", "coordinates": convert_ring(coords)}
    return None


def process_tile(tile: mercantile.Tile) -> list:
    raw = fetch_tile(tile)
    if not raw:
        return []
    try:
        decoded = mapbox_vector_tile.decode(raw)
    except Exception:
        return []
    bounds = mercantile.bounds(tile)
    out = []
    for layer_name in LAYERS:
        layer = decoded.get(layer_name)
        if not layer:
            continue
        for feat in layer["features"]:
            geom = convert_geometry(feat["geometry"], bounds)
            if geom is None:
                continue
            out.append({
                "type": "Feature",
                "properties": {"layer": layer_name, **feat["properties"]},
                "geometry": geom,
            })
    return out


def dedupe(features: list) -> list:
    seen = set()
    out = []
    for f in features:
        fid = f["properties"].get("id")
        layer = f["properties"].get("layer")
        key = (layer, fid)
        if fid is not None and key in seen:
            continue
        if fid is not None:
            seen.add(key)
        out.append(f)
    return out


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for region, bbox in REGION_BBOXES.items():
        tiles = list(mercantile.tiles(*bbox, [ZOOM]))
        print(f"{region}: {len(tiles)} tiles to fetch")
        features = []
        with ThreadPoolExecutor(max_workers=16) as ex:
            futures = [ex.submit(process_tile, t) for t in tiles]
            done = 0
            for fut in as_completed(futures):
                features.extend(fut.result())
                done += 1
                if done % 2000 == 0:
                    print(f"  {region}: {done}/{len(tiles)} tiles processed, {len(features)} raw features so far")
        features = dedupe(features)
        geojson = {"type": "FeatureCollection", "features": features}
        out_path = OUT_DIR / f"{region}_energia.geojson"
        out_path.write_text(json.dumps(geojson, ensure_ascii=False), encoding="utf-8")
        print(f"{region}: {len(features)} unique features -> {out_path}")


if __name__ == "__main__":
    main()
