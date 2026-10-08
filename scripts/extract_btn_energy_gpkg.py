"""Extract power plant / substation geometry from the official BTN GeoPackage.

Supersedes fetch_btn_energy_infra.py's vector-tile sweep now that the
authoritative source is available: data/raw/BTN_T_energia.gpkg, manually
downloaded from CNIG's cart (centrodedescargas.cnig.es/CentroDescargas/btn ->
"BTN Tema - Energía"). Tiles are simplified/clipped per zoom level for
rendering; this GeoPackage has the full, uncut geometry and attribute set,
so it should be treated as the source of truth going forward.

No geopandas/fiona/GDAL in this project's venv, so the GeoPackage is read
directly with sqlite3 (it's just SQLite) and geometries are decoded by
stripping the GeoPackage binary header and handing the remaining WKB to
shapely — see _decode_gpkg_geom().

Layers kept (same two as the tile-based fetch, for comparability):
- btn0713s_cen_elec (centrales eléctricas / power plants)
- btn0719s_tra_elec (transformación eléctrica / substations)

Both are stored in EPSG:4258 (ETRS89 geographic); reprojected to EPSG:4326
(WGS84) for consistency with the rest of the project's lat/lon outputs.
"""
import json
import sqlite3
from pathlib import Path

import shapely.wkb
from pyproj import Transformer
from shapely.geometry import mapping, shape
from shapely.ops import transform, unary_union

PROJECT_DIR = Path(__file__).resolve().parent.parent
GPKG_PATH = PROJECT_DIR / "data" / "raw" / "BTN_T_energia.gpkg"
CLEAN_DIR = PROJECT_DIR / "data" / "clean"
OUT_DIR = PROJECT_DIR / "data" / "raw" / "ign_btn_energia_gpkg"

LAYERS = ["btn0713s_cen_elec", "btn0719s_tra_elec"]

REGIONS = ["aragon", "catalunya"]

_to_wgs84 = Transformer.from_crs("EPSG:4258", "EPSG:4326", always_xy=True).transform


def _decode_gpkg_geom(blob: bytes):
    """Strip the GeoPackage binary header and parse the WKB tail with shapely.

    Header layout (OGC GeoPackage spec, section 2.1.3): 'G','P', version, flags,
    then a 4-byte srs_id, then an optional envelope whose length is encoded
    in bits 1-3 of the flags byte (0/32/48/48/64 bytes) before the WKB body.
    """
    if blob is None:
        return None
    flags = blob[3]
    envelope_code = (flags >> 1) & 0x07
    envelope_len = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[envelope_code]
    offset = 8 + envelope_len
    return shapely.wkb.loads(blob[offset:])


def load_region_boundary(region: str):
    path = CLEAN_DIR / region / f"boundary_{region}.geojson"
    data = json.loads(path.read_text(encoding="utf-8"))
    return unary_union([shape(f["geometry"]) for f in data["features"]])


def load_layer(con: sqlite3.Connection, layer: str) -> list:
    cur = con.execute(f"SELECT * FROM {layer}")
    cols = [d[0] for d in cur.description]
    geom_idx = cols.index("geometry")
    features = []
    for row in cur.fetchall():
        geom = _decode_gpkg_geom(row[geom_idx])
        if geom is None or geom.is_empty:
            continue
        geom = transform(_to_wgs84, geom)
        props = {"layer": layer, **{c: v for c, v in zip(cols, row) if c != "geometry"}}
        features.append((geom, props))
    return features


def main() -> None:
    con = sqlite3.connect(GPKG_PATH)
    boundaries = {region: load_region_boundary(region) for region in REGIONS}

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for region in REGIONS:
        region_features = []
        for layer in LAYERS:
            all_features = load_layer(con, layer)
            matched = [
                {"type": "Feature", "properties": props, "geometry": mapping(geom)}
                for geom, props in all_features
                if geom.intersects(boundaries[region])
            ]
            region_features.extend(matched)
            print(f"{region}/{layer}: {len(matched)} features (of {len(all_features)} nationwide)")

        out_path = OUT_DIR / f"{region}_energia.geojson"
        out_path.write_text(
            json.dumps({"type": "FeatureCollection", "features": region_features}, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"{region}: {len(region_features)} total -> {out_path}")

    con.close()


if __name__ == "__main__":
    main()
