"""Coordinate conversion between UTM and lat/lon.

Assumes ETRS89 / UTM zone 30N (EPSG:25830) — the CRS Spain's national
mapping uses for the whole Peninsula (Catalunya included, even though
it geographically sits in zone 31N), inferred from the e-distribución
coordinate ranges (see data/raw/README.md). Output lat/lon is WGS84
(EPSG:4326), the standard for web maps (Leaflet, Folium, etc.).

If a dataset turns out to use a different CRS, pass a different
`from_epsg`/`to_epsg` rather than editing the defaults, since other
scripts rely on them.
"""
from pyproj import Transformer

UTM_EPSG = "EPSG:25830"  # ETRS89 / UTM zone 30N
LATLON_EPSG = "EPSG:4326"  # WGS84


def utm_to_latlon(x, y, from_epsg: str = UTM_EPSG):
    """Convert UTM easting/northing (x, y) to (lat, lon) in WGS84.

    x, y can be scalars or array-like (e.g. a pandas Series) of equal length.
    """
    transformer = Transformer.from_crs(from_epsg, LATLON_EPSG, always_xy=True)
    lon, lat = transformer.transform(x, y)
    return lat, lon


def latlon_to_utm(lat, lon, to_epsg: str = UTM_EPSG):
    """Convert (lat, lon) in WGS84 to UTM easting/northing (x, y).

    lat, lon can be scalars or array-like (e.g. a pandas Series) of equal length.
    """
    transformer = Transformer.from_crs(LATLON_EPSG, to_epsg, always_xy=True)
    x, y = transformer.transform(lon, lat)
    return x, y


if __name__ == "__main__":
    # quick sanity check using the AEROP-HU substation from data/clean/aragon
    x, y = 721553.15, 4662582.49
    lat, lon = utm_to_latlon(x, y)
    print(f"UTM ({x}, {y}) -> lat/lon ({lat:.6f}, {lon:.6f})")
    x2, y2 = latlon_to_utm(lat, lon)
    print(f"round-trip -> UTM ({x2:.2f}, {y2:.2f})")
