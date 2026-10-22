# Grid data

Electricity-network data for Catalunya: access capacity at distribution (e-distribución, other distributors via CNMC) and transmission (REE) nodes.

- `raw/` — source snapshots. Not in the repo; download them by following the sections below.
- `clean/` — Catalunya tables generated from `raw/` by the scripts in `scripts/`. Kept in the repo.

**Month labels.** Every month named in this project is the month the data describes, not the month it was published. The sources publish at the start of a month what was true at the end of the previous one: e-distribución's file dated 2026-10-02 and REE's dated 2026-10-01 both describe **September 2026**, which is also how CNMC labels the same data. Raw file names follow this rule too (`2026_09_…`); each source's own file name and publication date are given in its section below.

**Current data month: September 2026** for all three capacity sources.

## Raw (`raw/`)

Immutable source snapshots. Do not edit these files in place — if a correction is needed, re-download and keep the old version for traceability.

### edistribucion_capacidad/

**Source:** e-distribución (Endesa's distribution arm) grid access capacity maps, published under CNMC Circular 1/2024 (Spanish regulator requirement for distributors to disclose available firm access capacity at network nodes above 1 kV).

- Demand page: https://www.edistribucion.com/es/red-electrica/nodos-capacidad-red/capacidad-demanda.html
- Generation page: https://www.edistribucion.com/es/red-electrica/nodos-capacidad-red/capacidad-generacion.html

e-distribución publishes a new file at the start of each month, and the two pages above keep every monthly file back to 2025-09.

**Files:**

| Data month | File here | e-distribución's file name | Published | Downloaded | In use |
|---|---|---|---|---|---|
| 2026-08 | `2026_08_demanda_edistribucion.xlsx`, `2026_08_generacion_edistribucion.xlsx` | `2026_09_03_R1299_demanda.xlsx`, `2026_09_03_R1299_generación.xlsx` | 2026-09-03 | 2026-09-17 | no, kept for traceability |
| 2026-09 | `2026_09_demanda_edistribucion.xlsx`, `2026_09_generacion_edistribucion.xlsx` | `2026_10_02_R1299_demanda.xlsx`, `2026_10_02_R1299_generación.xlsx` | 2026-10-02 | 2026-10-22 | yes |

The data month is inferred from the publication date (each workbook was created on the 1st–2nd of the month after) and confirmed for 2026-09 by CNMC, which labels the identical values as September 2026.

- `*_demanda_edistribucion.xlsx` — firm access capacity for new demand connections, per substation node and voltage level.
- `*_generacion_edistribucion.xlsx` — firm access capacity for new generation connections, per substation node and voltage level. Includes two extra columns (`Nudo Afección RdT`, `Nudo limitado por Scc`) flagging upstream transmission-network or short-circuit-capacity constraints.

**Coverage:** e-distribución's own network only — 10 Comunidades Autónomas (Andalucía, Aragón, Illes Balears, Canarias, Castilla y León, Castilla-La Mancha, Catalunya, Extremadura, Galicia, Navarra), 26 provinces, 1031 unique substations, 1850 rows in each file (one row per substation × voltage level combination).

Subset of interest for this project:
- Catalunya: 357 rows / 201 substations

**Known limitations:**
- Only the main e-distribución file was downloaded. The same pages also publish separate files for EASA and Ceuta (smaller distributors under the same corporate group) — not included here.
- i-DE (Iberdrola) is not relevant to this project's scope: it does not operate in Catalunya.
- No substation geolocation/geometry dataset yet. CNIG's BTN25 topographic dataset (national, includes substation point layer) was identified as the best candidate, but its download portal (centrodedescargas.cnig.es) is a JS-driven cart system that couldn't be scripted with `curl`/`WebFetch` — needs manual browser download or a headless-browser tool not currently installed.
- Only two data months are downloaded (2026-08 and 2026-09). Same 357 Catalunya nodes, columns, coordinates and upstream nodes in both; available capacity changed on 13 demand and 96 generation nodes between them. Older months can be downloaded from the same pages if a time series is needed.

### ree_capacidad_transporte/

**Source:** Red Eléctrica (REE), the transmission system operator. Monthly publication of access capacity at every transmission-network node (220/400 kV), calculated under the CNMC detail specifications.

- Demand page: https://www.ree.es/es/clientes/consumidor/acceso-conexion/conoce-la-capacidad-de-acceso
- Generation page: https://www.ree.es/es/clientes/generador/acceso-conexion/conoce-la-capacidad-de-acceso

**Data month:** 2026-09. REE's file names are `2026_10_01_GRT_demanda.xlsx` and `2026_10_01_GRT_generacion.xlsx`, published 2026-10-01 (workbook last modified 2026-09-30); downloaded 2026-10-08.

**Files:**
- `2026_09_demanda_ree.xlsx` — access capacity for demand and storage, per node. 102 columns under a four-row merged header.
- `2026_09_generacion_ree.xlsx` — access capacity for generation and storage, per node. 68 columns under a three-row merged header.

Each workbook has three sheets: `Ficha Capacidades` (the data), `Leyenda` (REE's definition of every column — read this before using a column) and `Zonas` (groups of nodes that share capacity as a zone).

**Coverage:** all of Spain, 937 node rows per file. Cataluña: 117 nodes (94 at 220 kV, 23 at 400 kV).

**Known limitations:**
- No coordinates — only node name, substation code and Comunidad Autónoma.
- Node names match the `Nudo Afección RdT` values in the e-distribución generation file for 72 of the 76 names used in Catalunya; `LESCORTS 220`, `R.CALDES 220`, `S.FOST 220` and `TANGER (CATALUÑA) 220` need a manual mapping.
- One data month only, not a time series.

### cnmc_mapas_capacidad/

**Source:** CNMC (Comisión Nacional de los Mercados y la Competencia, the energy regulator). The layers behind its two interactive capacity maps (demand and generation), built from the data every network operator must send it monthly under Circular 6/2025. Downloaded from the maps' public ArcGIS feature services by `scripts/fetch_cnmc_capacity_maps.py`.

- Map page: https://www.cnmc.es/sectores-que-regulamos/energia/supervision-del-mercado-electrico/informe-acceso-y-conexion-redes
- Services: https://services9.arcgis.com/F9FmuOlj5xjEjPRZ/arcgis/rest/services

**Data month:** 2026-09 (`periodo.json`). Downloaded 2026-10-15. CNMC labels data by the month it describes; its e-distribución values match e-distribución's 2026-09 file on all 357 Catalunya nodes. As of 2026-10-22 CNMC had not published a newer month.

**Files** (GeoJSON, WGS84, one point per node):
- `generacion_transporte.geojson` — 937 REE transmission nodes, generation and storage capacity.
- `demanda_transporte.geojson` — the same 937 nodes, demand and storage capacity.
- `generacion_distribucion.geojson` — 6,143 distribution nodes from ~60 distributors, generation capacity.
- `demanda_distribucion.geojson` — 6,180 distribution nodes, demand capacity.

**Join keys:** in the transmission layers, `NUDO_AFECCION_RDT` holds REE's exact node name (936 of 937 match the REE capacity files; `SAN MIGUEL DE SALINAS (SAN MIGUEL DE SALINAS B) 220` is the exception). `SUBESTACION` drops REE's "(X B)" suffix, so it is not unique. In the distribution layers, e-distribución rows match `raw/edistribucion_capacidad/` on `SUBESTACION` (name) + `NIVEL_TENSION`, with identical coordinates.

**Known limitations:**
- CNMC states the capacities are informative only. Capacity columns are simplified compared with REE's own files (one value per technology, no limiting criteria, no tender flags).
- `PROVINCIA` is wrong for a few transmission nodes: TORRENTE 400/220 (Valencia) and LA PEREDA 220 (Asturias) are labelled Girona.
- Distribution points are CNMC's conversion of each operator's UTM coordinates as zone 30N. At least one small distributor reports zone 31N (SE PLA ESTANY, AGRI-ENERGIA ELECTRICA), which puts the point ~500 km west.
- The ArcGIS services are what the public map loads; CNMC does not document them as a download, so their names or structure may change without notice.

## Clean (`clean/`)

Catalunya is the only target region, so every file name ends in `_catalunya`.

### e-distribución capacity

- `demanda_catalunya.csv` — 357 rows, 201 unique substations.
- `generacion_catalunya.csv` — 357 rows, 201 unique substations.

**Column changes from raw:** the source file repeats `Provincia` and `Municipio` twice (once as an INE numeric code, once as a human-readable label). These are renamed to disambiguate: `provincia_codigo`/`municipio_codigo` (code) vs. `provincia`/`municipio` (label). Two columns are added — `lat`, `lon` (WGS84) — converted from `Coordenada UTM X`/`Coordenada UTM Y` via `scripts/geo_utils.py`, assuming the source UTM values are ETRS89 / UTM zone 30N (EPSG:25830, see that script's docstring for why). All other columns are unchanged — see the Raw section above for field meanings.

**Not yet done:** demand and generation are still two separate files (joined only in `nodos_catalunya.csv`). Built from the 2026-09 data month. Re-run `scripts/filter_edistribucion.py` whenever a new month is downloaded — it overwrites these CSVs.

### REE transmission-node capacity

`ree_demanda_catalunya.csv` and `ree_generacion_catalunya.csv`, generated by `scripts/filter_ree_transporte.py` from the 2026-09 data month (see the Raw section above). One row per transmission node: Catalunya 117.

**Column changes from raw:** the multi-row merged header is flattened into one name per column, levels joined with ` | ` (e.g. `MARGEN DE CAPACIDAD DE ACCESO TOTAL | Almacenamiento | MPE [MW]`). Two columns are added — `nombre_nudo` and `tension_kv` — split from `Nombre y tensión del nudo`. Columns holding only numbers and `NA`/`N/A` markers are stored as numeric, with the markers as empty cells. No columns are dropped; definitions are in the raw workbook's `Leyenda` sheet.

Coordinates for the transmission nodes are in `cnmc_generacion_transporte_catalunya.csv`, joinable on `NUDO_AFECCION_RDT` = `Nombre y tensión del nudo` (all 117 match).

### Merged node table

`nodos_catalunya.csv`, generated by `scripts/merge_nodes.py`. One row per e-distribución node (substation × voltage level): Catalunya 357. Each row has the node's demand and generation capacity from e-distribución plus the situation of its upstream transmission node from REE, linked through e-distribución's `Nudo Afección RdT`.

**Every column name starts with its source:**

| Prefix | Source |
|---|---|
| `edis \| ` | e-distribución, identical in its demand and generation files (taken from the demand file) |
| `edis_dem \| ` | e-distribución demand file |
| `edis_gen \| ` | e-distribución generation file |
| `ree \| ` | REE, identical in its demand and generation files |
| `ree_dem \| ` | REE demand file |
| `ree_gen \| ` | REE generation file |

The one unprefixed column, `enlace_ree`, is added by the script and says how the row was linked to REE:

| Value | Meaning | Catalunya |
|---|---|---|
| `exacto` | upstream name found as-is in REE | 352 |
| `nombre corregido` | found after a spelling fix (`TANGER (CATALUÑA) 220` → `TANGER CATALUÑA 220`) | 2 |
| `dos nudos` | e-distribución names two upstream nodes; REE columns are left empty | 3 |
| `sin nudo` | upstream is `A determinar`; REE columns are left empty | 0 |

**Things to know before using it:**
- Both sources are from the same data month, 2026-09.
- The REE values describe the upstream transmission node, so they repeat on every e-distribución node under it. Do not sum `ree_*` columns across rows.
- Only a selection of REE columns is carried over (margins, available capacity, limiting criteria, reasons, tender flags — see `REE_SECTIONS` in the script). The rest are in `ree_*_catalunya.csv`, joinable on `ree | Nombre y tensión del nudo`.
- REE nodes that no e-distribución node points to are not in this table: 44 of 117 in Cataluña. Almost all of these have no connection positions towards the distribution network in REE's own data (41 of the 44).
- The upstream node can be in a neighbouring region (17 Catalunya rows hang off nodes in Aragón).
- `edis | municipio` comes from the demand file. The generation file differs only in apostrophe style and in the name of one municipality (C.ARO).

### Substation sites

`subestaciones_catalunya.csv`, generated by `scripts/classify_substations.py`. One row per physical substation site, classified into:

| `categoria` | Meaning | Catalunya |
|---|---|---|
| `1 TSO` | REE transmission substation with no distribution substation at the same spot | 25 |
| `2 TSO+DSO` | REE and at least one distributor's substation at the same spot | 73 |
| `3 DSO` | Distribution substation with no REE substation at the same spot | 157 |

A TSO site is one REE `Código de subestación` (it can hold both a 400 kV and a 220 kV node). A DSO site is one distributor substation: e-distribución's from its own files (201, one per `Subestación` code), every other distributor's from the CNMC layers (30, one per operator + `SUBESTACION` name). The code systems never overlap, so "same spot" is judged from distance, name and the upstream link — see the script's docstring for the rules.

**Where locations come from:** every TSO site is located by CNMC's transmission-node points (`tso | ubicacion` = `cnmc` for all 98). OpenStreetMap remains in the script as a fallback, unused for now. Distances are measured to the TSO site's nearest node point (ISONA's 400 kV and 220 kV points are 2.4 km apart, see `cnmc | dispersion_m`).

**Column prefixes:** `ree | ` and `cnmc | ` / `osm | ` describe the TSO side, by source. `dso | ` describes the DSO side, which mixes two sources, so the source is given per row in `dso | fuente` (`edis` or `cnmc`). Where each `dso | ` column comes from:

| Column | When `dso \| fuente` = `edis` (e-distribución files, via `nodos_catalunya.csv`) | When `dso \| fuente` = `cnmc` (`cnmc_*_distribucion_catalunya.csv`) |
|---|---|---|
| `dso \| id` | `R1-299` + `Subestación` (numeric code) | `GESTOR_RED` + `SUBESTACION` |
| `dso \| gestor` | fixed text `EDISTRIBUCIÓN REDES DIGITALES S.L.U.` (CNMC's `DESCRIPCION` for `R1-299`) | `DESCRIPCION` |
| `dso \| nombre` | `Nombre Subestación` | `SUBESTACION` |
| `dso \| tensiones_kv` | every `Nivel de Tensión (kV)` of the substation | every `NIVEL_TENSION` of the substation, demand and generation layers combined |
| `dso \| lat`, `dso \| lon` | `lat`, `lon` converted from `Coordenada UTM X/Y` as zone 30N | the layer's point geometry (CNMC's conversion), or the zone-31N correction from `filter_cnmc.py` |
| `dso \| coordenadas_corregidas` | always `False` | `coordenadas_corregidas` from `filter_cnmc.py` |
| `dso \| nudos aguas arriba` | `Nudo Afección RdT` (generation file), with the spelling fixes in `REE_NAME_FIXES` | `NUDO_AFECCION_RDT` (generation layer), with " kV" removed and `*` dropped |
| `dso \| fuente`, `dso \| n_sitios` | added by the script | added by the script |

**Unprefixed columns** (added by the script):
- `confianza` — for category 2: `alta` (≤ 300 m apart plus name or upstream agreement), `media` (TSO located only through the upstream link, or not located but name and upstream agree — none at the moment), `manual` (paired by a reviewed decision in `MANUAL_PAIRS`, see below). `a revisar` marks a site that might pair with another but is too far apart to decide automatically; it stays in its own category until reviewed (none at the moment).
- `distancia_m`, `evidencia` — distance to the TSO site and which evidence agreed, per DSO site.
- `lat`, `lon`, `fuente_coordenadas` — one location per site: the TSO point if there is one (`cnmc`, else `osm`), else the DSO point (`edis` or `cnmc`).

**Things to know before using it:**
- A category-2 site can hold more than one distributor: ADRALL has e-distribución and PEUSA. DSO columns are then joined with `; ` and `dso | n_sitios` gives the count.
- **Manual merges (decided 2026-10-22):** VANDELLOS 400 with e-distribución's VANDELLOS (447 m apart) and ASCÓ 400/220 with e-distribución's ASCO (869 m apart) are paired by hand, `confianza` = `manual`. Name and upstream agree in both cases but the distance is above the 300 m rule; both are in nuclear-plant areas, where one site can spread over several yards. Without this decision they would be `1 TSO` and `3 DSO`.
- Category 1 can still hide a distributor this data doesn't cover (private or industrial substations). MASDENVERGE 400, RIUDARENES 220 and VERNEDA 220 have connection positions towards the distribution network in REE's data but no matching DSO site.
- Most non-e-distribución DSO sites (27 of 30) are small, low-voltage and give no upstream node; some names look like boundary points between distributors rather than substations (`PF. ENDESA`).

### CNMC capacity-map nodes

`cnmc_<layer>_catalunya.csv`, generated by `scripts/filter_cnmc.py` from `raw/cnmc_mapas_capacidad/`. One row per node, all CNMC attributes kept, plus `lat`/`lon` from the point geometry and `coordenadas_corregidas`.

| Layer | Catalunya |
|---|---|
| `generacion_transporte` (REE) | 117 |
| `demanda_transporte` (REE) | 117 |
| `generacion_distribucion` (all distributors) | 393 (14 operators) |
| `demanda_distribucion` (all distributors) | 395 (15 operators) |

**Region selection:** by `PROVINCIA`, dropping rows whose point lies more than ~10 km outside the region (removes TORRENTE and LA PEREDA, mislabelled as Girona). If a distribution point is far outside but its UTM values land inside when read as zone 31N, the corrected point is kept and `coordenadas_corregidas` is `True` (SE PLA ESTANY in Catalunya).

**Used by:** `subestaciones_catalunya.csv` takes its transmission-node locations and its non-e-distribución substations from these files. Not joined to `nodos_catalunya.csv`.

**Capacity fields:** the transmission layers' capacity columns are a simplified version of REE's; no reliable one-to-one mapping to REE's columns was found (most values are 0 in both, which hides any mismatch). Use `ree_*_catalunya.csv` for transmission capacity, and the CNMC transmission layers for location only.
