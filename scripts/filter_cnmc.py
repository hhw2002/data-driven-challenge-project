"""Filter the CNMC capacity-map layers (raw GeoJSON) into per-region CSVs.

One CSV per layer and region, every attribute kept, plus lat/lon from the
point geometry (WGS84). Regions are selected by CNMC's PROVINCIA field,
dropping rows whose point lies far outside the region: a few transmission
nodes carry the wrong province (TORRENTE in Valencia and LA PEREDA in
Asturias are labelled "Girona"), while their municipality and point are right.

Distribution nodes also carry the operator's own UTM coordinates. CNMC
converts them as zone 30N, but a few small distributors report zone 31N, which
throws the point ~500 km west (SE PLA ESTANY lands in Burgos). When an
in-province point is far outside the region, its UTM values are re-read as
zone 31N; if that lands inside, the corrected point is kept and flagged in
`coordenadas_corregidas`.
Writes data/grid/clean/cnmc_<layer>_<region>.csv.
"""
import json
from pathlib import Path

import pandas as pd
import shapely
from shapely.geometry import shape
from shapely.ops import unary_union

from geo_utils import utm_to_latlon

PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "data" / "grid" / "raw" / "cnmc_mapas_capacidad"
CLEAN_DIR = PROJECT_DIR / "data" / "grid" / "clean"
GIS_CLEAN_DIR = PROJECT_DIR / "data" / "gis" / "clean"

LAYERS = ["generacion_transporte", "demanda_transporte", "generacion_distribucion", "demanda_distribucion"]

REGIONS = {
    "catalunya": ["Barcelona", "Girona", "Lleida", "Tarragona"],
}

# tolerance around the (simplified) region outline, in degrees (~10 km)
BOUNDARY_TOLERANCE_DEG = 0.1

UTM_ZONE_31N = "EPSG:25831"


def load_boundary(region_key: str):
    path = GIS_CLEAN_DIR / f"boundary_{region_key}.geojson"
    features = json.loads(path.read_text(encoding="utf-8"))["features"]
    area = unary_union([shape(f["geometry"]) for f in features]).buffer(BOUNDARY_TOLERANCE_DEG)
    shapely.prepare(area)
    return area


def load_layer(name: str) -> pd.DataFrame:
    features = json.loads((RAW_DIR / f"{name}.geojson").read_text(encoding="utf-8"))["features"]
    rows = []
    for f in features:
        lon, lat = f["geometry"]["coordinates"]
        rows.append({**f["properties"], "lat": lat, "lon": lon})
    return pd.DataFrame(rows)


def main() -> None:
    period = json.loads((RAW_DIR / "periodo.json").read_text(encoding="utf-8"))
    print(f"data period: {period['MES']} {period['ANIO']}")
    for name in LAYERS:
        df = load_layer(name)
        df["coordenadas_corregidas"] = False
        for region_key, provinces in REGIONS.items():
            area = load_boundary(region_key)
            in_province = df["PROVINCIA"].isin(provinces)
            near_region = shapely.contains(area, shapely.points(df["lon"].values, df["lat"].values))
            if "COORDENADA_UTM_X" in df.columns:
                suspect = in_province & ~near_region
                lat31, lon31 = utm_to_latlon(
                    df.loc[suspect, "COORDENADA_UTM_X"], df.loc[suspect, "COORDENADA_UTM_Y"], from_epsg=UTM_ZONE_31N
                )
                fixed = pd.Series(shapely.contains(area, shapely.points(lon31, lat31)), index=df.index[suspect])
                fixed = fixed[fixed].index
                df.loc[fixed, "lat"] = pd.Series(lat31, index=df.index[suspect])[fixed]
                df.loc[fixed, "lon"] = pd.Series(lon31, index=df.index[suspect])[fixed]
                df.loc[fixed, "coordenadas_corregidas"] = True
                near_region = near_region | df.index.isin(fixed)
                if len(fixed):
                    print(f"  {region_key}/{name}: re-read {len(fixed)} point(s) as UTM zone 31N: "
                          + ", ".join(df.loc[fixed, "SUBESTACION"].astype(str)))
            dropped = df[in_province & ~near_region]
            if len(dropped):
                names = ", ".join(f"{s} {kv} ({m})" for s, kv, m in dropped[["SUBESTACION", "NIVEL_TENSION", "MUNICIPIO"]].values)
                print(f"  {region_key}/{name}: dropped {len(dropped)} labelled in-region but located elsewhere: {names}")
            subset = df[in_province & near_region]
            out_path = CLEAN_DIR / f"cnmc_{name}_{region_key}.csv"
            subset.to_csv(out_path, index=False)
            print(f"{region_key}/cnmc_{name}: {len(subset)} nodes, "
                  f"{subset['DESCRIPCION'].nunique()} network operators -> {out_path}")


if __name__ == "__main__":
    main()
