# Raw Data

Immutable source snapshots. Do not edit these files in place — if a correction is needed, re-download and keep the old version for traceability.

## edistribucion_capacidad/

**Source:** e-distribución (Endesa's distribution arm) grid access capacity maps, published under CNMC Circular 1/2024 (Spanish regulator requirement for distributors to disclose available firm access capacity at network nodes above 1 kV).

- Demand page: https://www.edistribucion.com/es/red-electrica/nodos-capacidad-red/capacidad-demanda.html
- Generation page: https://www.edistribucion.com/es/red-electrica/nodos-capacidad-red/capacidad-generacion.html

**Downloaded:** 2026-09-17. Snapshot dated 2026-09-03 (filename encodes the publication month; e-distribución updates this monthly).

**Files:**
- `2026_09_demanda_edistribucion.xlsx` — firm access capacity for new demand connections, per substation node and voltage level.
- `2026_09_generacion_edistribucion.xlsx` — firm access capacity for new generation connections, per substation node and voltage level. Includes two extra columns (`Nudo Afección RdT`, `Nudo limitado por Scc`) flagging upstream transmission-network or short-circuit-capacity constraints.

**Coverage:** e-distribución's own network only — 10 Comunidades Autónomas (Andalucía, Aragón, Illes Balears, Canarias, Castilla y León, Castilla-La Mancha, Catalunya, Extremadura, Galicia, Navarra), 26 provinces, 1031 unique substations, 1850 rows in each file (one row per substation × voltage level combination).

Subset of interest for this project:
- Aragón: 457 rows / 244 substations
- Catalunya: 357 rows / 201 substations

**Known limitations:**
- Only the main e-distribución file was downloaded. The same pages also publish separate files for EASA and Ceuta (smaller distributors under the same corporate group) — not included here.
- i-DE (Iberdrola) is not relevant to this project's scope: it does not operate in Aragón or Catalunya.
- No substation geolocation/geometry dataset yet. CNIG's BTN25 topographic dataset (national, includes substation point layer) was identified as the best candidate, but its download portal (centrodedescargas.cnig.es) is a JS-driven cart system that couldn't be scripted with `curl`/`WebFetch` — needs manual browser download or a headless-browser tool not currently installed.
- This is a single monthly snapshot, not a time series. Re-download if trend data over time is needed.
