"""Download the layers behind CNMC's interactive grid-capacity maps.

CNMC (the energy regulator) publishes two ArcGIS maps, one for demand and
one for generation, built from the capacity data every network operator
must send it each month (Circular 6/2025). The maps read from public
ArcGIS feature services; this pulls every feature from each of them as
GeoJSON in WGS84, so every node comes with a point location:

- Generacion_en_Transporte / Demanda_en_Transporte_v2: REE's transmission
  nodes (220/400 kV), one point per node.
- Generacion_en_Distribucion / Demanda_en_Distribucion: every distributor's
  nodes (e-distribución, i-DE and ~60 smaller ones), one point per node.
- Capacidad_Periodo: one row naming the month the data refers to.

Map pages: https://www.cnmc.es/sectores-que-regulamos/energia/supervision-del-mercado-electrico/informe-acceso-y-conexion-redes
CNMC states the capacities are informative only.
"""
import json
from pathlib import Path

import requests

PROJECT_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_DIR / "data" / "grid" / "raw" / "cnmc_mapas_capacidad"

SERVICES_URL = "https://services9.arcgis.com/F9FmuOlj5xjEjPRZ/arcgis/rest/services"

# output name -> layer path under SERVICES_URL
LAYERS = {
    "generacion_transporte": "Generacion_en_Transporte/FeatureServer/0",
    "demanda_transporte": "Demanda_en_Transporte_v2/FeatureServer/11",
    "generacion_distribucion": "Generacion_en_Distribucion/FeatureServer/4",
    "demanda_distribucion": "Demanda_en_Distribucion/FeatureServer/4",
}
PERIOD_LAYER = "Capacidad_Periodo/FeatureServer/10"

PAGE_SIZE = 2000  # the services' maxRecordCount

session = requests.Session()


def query(layer: str, **params) -> dict:
    resp = session.get(f"{SERVICES_URL}/{layer}/query", params=params, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"{layer}: {data['error']}")
    return data


def fetch_layer(layer: str) -> dict:
    """All features of a layer as one GeoJSON FeatureCollection (EPSG:4326)."""
    expected = query(layer, where="1=1", returnCountOnly="true", f="json")["count"]
    features = []
    while len(features) < expected:
        page = query(
            layer, where="1=1", outFields="*", outSR=4326, f="geojson",
            orderByFields="OBJECTID", resultOffset=len(features), resultRecordCount=PAGE_SIZE,
        )
        if not page["features"]:
            break
        features.extend(page["features"])
    if len(features) != expected:
        raise RuntimeError(f"{layer}: got {len(features)} features, service reports {expected}")
    return {"type": "FeatureCollection", "features": features}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    period = query(PERIOD_LAYER, where="1=1", outFields="*", f="json")["features"][0]["attributes"]
    (OUT_DIR / "periodo.json").write_text(json.dumps(period, ensure_ascii=False), encoding="utf-8")
    print(f"data period: {period['MES']} {period['ANIO']}")

    for name, layer in LAYERS.items():
        collection = fetch_layer(layer)
        out_path = OUT_DIR / f"{name}.geojson"
        out_path.write_text(json.dumps(collection, ensure_ascii=False), encoding="utf-8")
        print(f"{name}: {len(collection['features'])} nodes -> {out_path}")


if __name__ == "__main__":
    main()
