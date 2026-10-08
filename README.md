# Data Driven Challenge Project

Course project for 240295 Data-Driven Challenges for Energy Engineering (UPC, autumn 2026).

**Research question:** how can public energy and geospatial data be combined to identify and rank promising areas for grid-scale battery storage (BESS) in Catalonia?

**Live maps:** https://hhw2002.github.io/data-driven-challenge-project/

## Status

The project is at an early stage. What exists today is the grid layer only: available access capacity per e-distribución substation, shown as an interactive map for Catalunya and Aragón. Aragón is left over from an earlier comparison idea; the project scope is now Catalonia.

Not built yet:

- the renewables, demand and land layers
- joining demand and generation capacity into one table per substation
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
3. **Quartiles of the rest.** Among the substations with more than 0 MW, the 25th, 50th and 75th percentiles are calculated. These three values split those substations into four classes of roughly equal size, from lowest to highest capacity.
4. **Rounding.** The three percentile values are rounded to 0.1 MW before the substations are classified, so the ranges in the legend are exactly the ranges used. The upper bound of each range is inclusive.

The percentiles are calculated separately for each region, so the MW ranges differ between the two maps. They also change whenever a new monthly snapshot is loaded.

With the September 2026 snapshot:

| Class | Catalunya | Substations | Aragón | Substations |
|---|---|---|---|---|
| No capacity | 0 MW | 182 | 0 MW | 232 |
| Lowest quarter | > 0 – 8.9 MW | 5 | > 0 – 4.8 MW | 3 |
| Second quarter | > 8.9 – 17.0 MW | 5 | > 4.8 – 17.7 MW | 3 |
| Third quarter | > 17.0 – 30.4 MW | 4 | > 17.7 – 28.6 MW | 3 |
| Highest quarter | > 30.4 MW | 5 | > 28.6 MW | 3 |

Because most substations have no available capacity, each quarter holds only a few substations. A class says how a substation compares with the others that still have capacity; it does not say what share of that substation's own capacity is free.

Each class is a separate layer, so the layer list in the top-right corner of the map works as a filter: untick a class to hide it.

## Repository layout

| Path | Contents |
|---|---|
| `scripts/` | Data download, cleaning and plotting scripts |
| `data/clean/` | Cleaned per-region data, small enough to keep in the repo |
| `data/raw/` | Source snapshots; not in the repo (about 800 MB), only its `README.md` is |
| `docs/` | Generated maps, published with GitHub Pages |

## Scripts

| Script | What it does | Needs raw data |
|---|---|---|
| `plot_capacity_map.py` | Draws the substation maps into `docs/` | No |
| `filter_edistribucion.py` | Splits the e-distribución capacity files into per-region CSVs and adds lat/lon | Yes |
| `filter_boundaries.py` | Splits the national province boundaries into per-region GeoJSON | Yes |
| `fetch_ign_boundaries.py` | Downloads official province boundaries from the IGN web service | Downloads it |
| `extract_btn_energy_gpkg.py` | Extracts power plant and substation shapes from the IGN BTN GeoPackage | Yes |
| `fetch_btn_energy_infra.py` | Older tile-based version of the above, superseded | Downloads it |
| `geo_utils.py` | Coordinate conversion helpers used by the other scripts | No |

Only `plot_capacity_map.py` runs straight after cloning. To run the others, download the source files first by following `data/raw/README.md`.

## Data sources

- **e-distribución** grid access capacity maps (demand and generation), snapshot of September 2026.
- **IGN / CNIG** province boundaries and the BTN energy infrastructure layer.

Details, download dates and known limitations are in `data/raw/README.md` and `data/clean/README.md`.

## Known limitations

- The capacity data covers e-distribución's distribution network only, not REE's transmission nodes.
- It is a single monthly snapshot, not a time series.
- Substation coordinates are assumed to be ETRS89 / UTM zone 30N (EPSG:25830); see `scripts/geo_utils.py`.
