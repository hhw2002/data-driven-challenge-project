"""Plot substation capacity on a map: province boundary outline + points.

For each region (aragon, catalunya), reads:
- data/clean/<region>/boundary_<region>.geojson
- data/clean/<region>/demanda_<region>.csv
and writes an interactive HTML map to docs/map_<region>.html, plus a
docs/index.html landing page linking to each map. docs/ is the folder
GitHub Pages publishes.
"""
from pathlib import Path

import folium
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
CLEAN_DIR = PROJECT_DIR / "data" / "clean"
DOCS_DIR = PROJECT_DIR / "docs"

REGIONS = ["aragon", "catalunya"]

CAPACITY_COL = "Capacidad firme disponible (MW)"


def build_map(region_key: str) -> Path:
    region_dir = CLEAN_DIR / region_key
    boundary_path = region_dir / f"boundary_{region_key}.geojson"
    demand_path = region_dir / f"demanda_{region_key}.csv"

    df = pd.read_csv(demand_path)
    # one marker per substation: sum capacity across its voltage levels
    stations = df.groupby("Nombre Subestación").agg(
        lat=("lat", "first"),
        lon=("lon", "first"),
        municipio=("municipio", "first"),
        capacidad_mw=(CAPACITY_COL, "sum"),
    ).reset_index()

    m = folium.Map(location=[stations["lat"].mean(), stations["lon"].mean()], zoom_start=8)

    folium.GeoJson(
        str(boundary_path),
        name="province boundary",
        style_function=lambda _: {"fillOpacity": 0, "color": "#444444", "weight": 2},
    ).add_to(m)

    for _, row in stations.iterrows():
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=4,
            color="#d62728",
            fill=True,
            fill_opacity=0.8,
            popup=(
                f"<b>{row['Nombre Subestación']}</b><br>"
                f"{row['municipio']}<br>"
                f"Available firm demand capacity: {row['capacidad_mw']:.2f} MW"
            ),
        ).add_to(m)

    out_path = DOCS_DIR / f"map_{region_key}.html"
    m.save(str(out_path))
    return out_path


def build_index(map_paths: list[Path]) -> Path:
    links = "\n".join(
        f'    <li><a href="{p.name}">{p.stem.removeprefix("map_").title()}</a></li>'
        for p in map_paths
    )
    out_path = DOCS_DIR / "index.html"
    out_path.write_text(
        "<!doctype html>\n"
        '<html lang="en">\n<head>\n  <meta charset="utf-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "  <title>Data Driven Challenge Project</title>\n</head>\n<body>\n"
        "  <h1>Data Driven Challenge Project</h1>\n"
        "  <p>Available firm demand capacity per e-distribución substation.</p>\n"
        f"  <ul>\n{links}\n  </ul>\n</body>\n</html>\n",
        encoding="utf-8",
    )
    return out_path


def main() -> None:
    DOCS_DIR.mkdir(exist_ok=True)
    map_paths = []
    for region_key in REGIONS:
        out_path = build_map(region_key)
        map_paths.append(out_path)
        print(f"{region_key} -> {out_path}")
    print(f"index -> {build_index(map_paths)}")


if __name__ == "__main__":
    main()
