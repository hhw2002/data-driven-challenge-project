# Data Driven Challenge Project

Course project for 240295 Data-Driven Challenges for Energy Engineering (UPC, autumn 2026).

**Research question:** how can public energy and geospatial data be combined to identify and rank promising areas for grid-scale battery storage (BESS) in Catalonia?

**GitHub repo:** https://github.com/hhw2002/data-driven-challenge-project (public)

**Live maps:** https://hhw2002.github.io/data-driven-challenge-project/

## Status

The project is at an early stage. What exists today is the grid layer only: available access capacity per e-distribución substation, shown as an interactive map for Catalunya, plus cleaned tables that link it to REE's transmission nodes and classify every substation site (see `data/grid/README.md`). The project covers Catalunya only.

Not built yet:

- the renewables, demand and land layers
- the BESS opportunity score and ranking

## Run it

Requires Python 3 (developed on 3.14).

```bash
git clone https://github.com/hhw2002/data-driven-challenge-project.git
cd data-driven-challenge-project
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/plot_capacity_map.py
```

This rebuilds the maps in `docs/` from the cleaned data in the repo. Open `docs/index.html` in a browser to view them; an internet connection is needed because the base map loads online.

## Update the live maps

GitHub Pages publishes the `docs/` folder on the `main` branch. Re-run the plot script, commit, and push; the site updates about a minute later.

## How the capacity classes are calculated

Each substation is coloured by its available firm demand capacity, in MW. The MW ranges in the map legend are calculated from the data, not chosen by hand:

1. **Capacity per substation.** The source file has one row per substation and voltage level. The column `Capacidad firme disponible (MW)` is summed over all voltage levels of a substation, so each substation gets one value.
2. **Zero class.** Substations whose total is exactly 0 MW form their own class, "0 MW (no capacity)".
3. **Quartiles of the rest.** Among the Catalunya substations with more than 0 MW, the 25th, 50th and 75th percentiles are calculated. These three values split those substations into four classes of roughly equal size, from lowest to highest capacity.
4. **Rounding.** The three percentile values are rounded to 0.1 MW before the substations are classified, so the ranges in the legend are exactly the ranges used. The upper bound of each range is inclusive.

The ranges change whenever a new monthly snapshot is loaded.

With the October 2026 file (dated 2026-10-02):

| Class | MW range | Catalunya substations |
|---|---|---|
| No capacity | 0 MW | 183 |
| Lowest quarter | > 0 – 7.8 MW | 5 |
| Second quarter | > 7.8 – 20.7 MW | 4 |
| Third quarter | > 20.7 – 25.9 MW | 4 |
| Highest quarter | > 25.9 MW | 5 |

Because most substations have no available capacity, each quarter holds only a few substations. A class says how a substation compares with the Catalunya substations that still have capacity; it does not say what share of that substation's own capacity is free.

Each class is a separate layer, so the layer list in the top-right corner of the map works as a filter: untick a class to hide it.

## Repository layout

| Path | Contents |
|---|---|
| `scripts/` | Data download, cleaning and plotting scripts |
| `data/grid/` | Electricity-network data: e-distribución, REE and CNMC access capacity. `clean/` is in the repo, `raw/` is not |
| `data/gis/` | Geographic layers: province boundaries, IGN BTN energy layers, OSM substations. `clean/` is in the repo, `raw/` is not |
| `docs/` | Generated maps, published with GitHub Pages |

## Scripts

| Script | What it does | Needs raw data |
|---|---|---|
| `plot_capacity_map.py` | Draws the substation maps into `docs/` | No |
| `filter_edistribucion.py` | Filters the e-distribución capacity files to Catalunya and adds lat/lon | Yes |
| `filter_boundaries.py` | Filters the national province boundaries to Catalunya | Yes |
| `fetch_ign_boundaries.py` | Downloads official province boundaries from the IGN web service | Downloads it |
| `extract_btn_energy_gpkg.py` | Extracts power plant and substation shapes from the IGN BTN GeoPackage | Yes |
| `fetch_btn_energy_infra.py` | Older tile-based version of the above, superseded | Downloads it |
| `filter_ree_transporte.py` | Flattens REE's transmission-node capacity workbooks and filters them to Catalunya | Yes |
| `merge_nodes.py` | Joins e-distribución demand and generation per node and adds the upstream REE node's capacity | Yes |
| `fetch_cnmc_capacity_maps.py` | Downloads the layers behind CNMC's capacity maps (all nodes, with coordinates) | Downloads it |
| `filter_cnmc.py` | Filters the CNMC layers to Catalunya and fixes known location errors | Yes |
| `fetch_osm_substations.py` | Downloads 220/400 kV substations from OpenStreetMap (fallback locations) | Downloads it |
| `classify_substations.py` | Classifies every substation site as TSO only, TSO + DSO or DSO only | Yes |
| `geo_utils.py` | Coordinate conversion helpers used by the other scripts | No |

Only `plot_capacity_map.py` runs straight after cloning. To run the others, download the source files first by following `data/grid/README.md` and `data/gis/README.md`.

## Data sources

- **e-distribución** grid access capacity per distribution node (demand and generation), file dated 2026-10-02.
- **REE** access capacity per transmission node (demand and generation), file dated 2026-10-01.
- **CNMC** capacity maps: every network operator's nodes with coordinates, data period September 2026 (the same content as the e-distribución October file).
- **OpenStreetMap** 220/400 kV substations, kept as a fallback location source.
- **IGN / CNIG** province boundaries and the BTN energy infrastructure layer.

Details, download dates and known limitations are in `data/grid/README.md` and `data/gis/README.md`.

## Known limitations

- The capacity data is one point in time (end of September 2026), not a time series. All three sources publish monthly, so one can be built by downloading again.
- The map still shows e-distribución's demand capacity only; REE's transmission capacity and the other distributors are in the cleaned tables but not on the map yet.
- Substation coordinates are assumed to be ETRS89 / UTM zone 30N (EPSG:25830); see `scripts/geo_utils.py`.
