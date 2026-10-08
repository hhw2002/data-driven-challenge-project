"""Plot substation capacity on a map: province boundary outline + points.

For each region (aragon, catalunya), reads:
- data/clean/<region>/boundary_<region>.geojson
- data/clean/<region>/demanda_<region>.csv
and writes an interactive HTML map to docs/map_<region>.html, plus a
docs/index.html landing page linking to each map. docs/ is the folder
GitHub Pages publishes.

Substations are coloured by capacity class: one class for 0 MW, then the
quartiles of the Catalunya substations that do have capacity (see
quartile_thresholds()). Every region uses those same MW ranges, so the
maps are directly comparable. Each class is its own map layer, so the
layer control doubles as a filter.
"""
from pathlib import Path

import folium
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
CLEAN_DIR = PROJECT_DIR / "data" / "clean"
DOCS_DIR = PROJECT_DIR / "docs"

REGIONS = ["aragon", "catalunya"]
# the region whose quartiles define the MW ranges used on every map
THRESHOLD_REGION = "catalunya"

CAPACITY_COL = "Capacidad firme disponible (MW)"

# neutral grey for "no capacity", then one blue hue light -> dark for the quartiles
ZERO_COLOR = "#8a8a86"
QUARTILE_COLORS = ["#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]


def load_stations(region_key: str) -> pd.DataFrame:
    """One row per substation: capacity summed across its voltage levels."""
    df = pd.read_csv(CLEAN_DIR / region_key / f"demanda_{region_key}.csv")
    stations = df.groupby("Nombre Subestación").agg(
        lat=("lat", "first"),
        lon=("lon", "first"),
        municipio=("municipio", "first"),
        capacidad_mw=(CAPACITY_COL, "sum"),
    ).reset_index()
    stations["capacidad_mw"] = stations["capacidad_mw"].round(2)
    return stations


def quartile_thresholds(capacity: pd.Series) -> tuple[float, float, float]:
    """25th/50th/75th percentiles of the substations with capacity > 0.

    Rounded to 0.1 MW *before* classifying, so the MW ranges shown in the
    legend are exactly the ranges used.
    """
    return tuple(capacity[capacity > 0].quantile([0.25, 0.5, 0.75]).round(1))


def capacity_classes(
    capacity: pd.Series, thresholds: tuple[float, float, float]
) -> tuple[pd.Series, list[dict]]:
    """Assign each substation a capacity class and describe the classes.

    Class 0 is exactly 0 MW. Classes 1-4 split capacity > 0 at the three
    thresholds. Upper bounds are inclusive.
    """
    q1, q2, q3 = thresholds
    labels = [
        "0 MW (no capacity)",
        f"> 0 – {q1:.1f} MW",
        f"> {q1:.1f} – {q2:.1f} MW",
        f"> {q2:.1f} – {q3:.1f} MW",
        f"> {q3:.1f} MW",
    ]
    class_idx = capacity.apply(
        lambda mw: 0 if mw == 0 else 1 + sum(mw > q for q in (q1, q2, q3))
    )
    classes = [
        {"label": label, "color": color, "count": int((class_idx == i).sum())}
        for i, (label, color) in enumerate(zip(labels, [ZERO_COLOR] + QUARTILE_COLORS))
    ]
    return class_idx, classes


def _swatch(color: str) -> str:
    return (
        f'<span style="display:inline-block;width:12px;height:12px;border-radius:50%;'
        f'background:{color};border:1px solid #ffffff;box-shadow:0 0 0 1px #9a9a96;'
        f'margin-right:6px;vertical-align:-1px;"></span>'
    )


def _legend_html(classes: list[dict]) -> str:
    rows = "".join(
        f'<div style="margin-top:4px;">{_swatch(c["color"])}{c["label"]}'
        f'<span style="color:#6b6b68;"> · {c["count"]}</span></div>'
        for c in classes
    )
    return (
        '<div style="position:fixed;bottom:24px;left:12px;z-index:1000;'
        "background:#ffffff;color:#1f1f1e;padding:10px 12px;border-radius:6px;"
        "box-shadow:0 1px 4px rgba(0,0,0,0.3);font:13px/1.3 'Open Sans',Arial,sans-serif;"
        'max-width:260px;">'
        "<b>Available firm demand capacity</b>"
        '<div style="color:#6b6b68;">per substation · number of substations</div>'
        f"{rows}</div>"
    )


def build_map(region_key: str, thresholds: tuple[float, float, float]) -> Path:
    boundary_path = CLEAN_DIR / region_key / f"boundary_{region_key}.geojson"

    stations = load_stations(region_key)
    stations["class_idx"], classes = capacity_classes(stations["capacidad_mw"], thresholds)

    m = folium.Map(location=[stations["lat"].mean(), stations["lon"].mean()], zoom_start=8)

    folium.GeoJson(
        str(boundary_path),
        name="Province boundary",
        style_function=lambda _: {"fillOpacity": 0, "color": "#444444", "weight": 2},
    ).add_to(m)

    # one layer per class, added lowest first so substations with capacity draw on top
    for idx, cls in enumerate(classes):
        layer = folium.FeatureGroup(name=f"{_swatch(cls['color'])}{cls['label']}")
        for _, row in stations[stations["class_idx"] == idx].iterrows():
            folium.CircleMarker(
                location=[row["lat"], row["lon"]],
                radius=5 if idx == 0 else 7,
                color="#ffffff",
                weight=1.5,
                fill=True,
                fill_color=cls["color"],
                fill_opacity=0.75 if idx == 0 else 1,
                tooltip=f"{row['Nombre Subestación']}: {row['capacidad_mw']:.2f} MW",
                popup=folium.Popup(
                    f"<b>{row['Nombre Subestación']}</b><br>"
                    f"{row['municipio']}<br>"
                    f"Available firm demand capacity: {row['capacidad_mw']:.2f} MW<br>"
                    f"Capacity range: {cls['label']}",
                    max_width=280,
                ),
            ).add_to(layer)
        layer.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    m.get_root().html.add_child(folium.Element(_legend_html(classes)))

    print(f"{region_key} capacity classes:")
    for cls in classes:
        print(f"  {cls['label']:<22} {cls['count']:>4} substations")

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
        "  <p>Available firm demand capacity per e-distribución substation, "
        "coloured by capacity class.</p>\n"
        f"  <ul>\n{links}\n  </ul>\n</body>\n</html>\n",
        encoding="utf-8",
    )
    return out_path


def main() -> None:
    DOCS_DIR.mkdir(exist_ok=True)
    thresholds = quartile_thresholds(load_stations(THRESHOLD_REGION)["capacidad_mw"])
    map_paths = []
    for region_key in REGIONS:
        out_path = build_map(region_key, thresholds)
        map_paths.append(out_path)
        print(f"{region_key} -> {out_path}")
    print(f"index -> {build_index(map_paths)}")


if __name__ == "__main__":
    main()
