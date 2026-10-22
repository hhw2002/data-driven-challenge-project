"""Classify every substation site as TSO only, TSO + DSO, or DSO only.

A site is one physical substation. TSO sites come from REE (one per
"Código de subestación", which can hold a 400 kV and a 220 kV node). DSO
sites come from every distributor: e-distribución from its own capacity
files (one per "Subestación" code, via nodos_<region>.csv), the ~15 smaller
ones from CNMC's capacity map (one per operator + substation name). TSO and
DSO code systems never overlap, so a TSO site and a DSO site are judged to
be the same spot from three pieces of evidence:

- distance: the DSO point against the TSO site's nearest node point. TSO
  points come from CNMC's capacity map (REE publishes none); OpenStreetMap
  is only a fallback for nodes CNMC doesn't cover — by name, or the
  unclaimed OSM 220/400 kV substation right next to a DSO site that names
  this TSO site as upstream;
- name: the two names are similar after normalising (see same_name());
- upstream: the DSO lists that TSO site as the node's upstream transmission
  node ("Nudo Afección RdT").

Pairing rules, in order:
- "alta": within MAX_DIST_M and at least one of name / upstream, with the
  TSO site located by CNMC or by OSM name.
- "media": within MAX_DIST_M of a TSO site located through its upstream
  link (the location and the pairing rest on the same evidence), or TSO
  site not located at all but both name and upstream agree.
- "a revisar": name and upstream agree but the sites are further apart
  than MAX_DIST_M, and neither is paired with anything else. Left unpaired
  (each stays in its own category) until someone checks it; record the
  decision in MANUAL_PAIRS.

One TSO site can share its spot with several distributors (e.g. ADRALL:
e-distribución and PEUSA), so a "2 TSO+DSO" row can list more than one
DSO site, joined with "; ".

Column prefixes: "ree | " and "cnmc | " / "osm | " for the TSO side by
source; "dso | " for the DSO side, whose source is given per row in
"dso | fuente" (edis or cnmc). Unprefixed columns are added here.
"""
import difflib
import json
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

from filter_ree_transporte import FILES as REE_FILES
from filter_ree_transporte import NODE_COL, read_sheet

PROJECT_DIR = Path(__file__).resolve().parent.parent
CLEAN_DIR = PROJECT_DIR / "data" / "grid" / "clean"
OSM_DIR = PROJECT_DIR / "data" / "gis" / "raw" / "osm_subestaciones"

REGIONS = {"catalunya": "Cataluña"}

MAX_DIST_M = 300
# how close an OSM name must be to an REE name to use it as that site's location
OSM_NAME_MIN = 0.85
# OSM candidates further apart than this are treated as different places
OSM_SPREAD_MAX_M = 500

EDIS_GESTOR = "R1-299"
EDIS_NAME = "EDISTRIBUCIÓN REDES DIGITALES S.L.U."
UPSTREAM_COL = "edis_gen | Nudo Afección RdT"
# DSOs spell a few transmission nodes differently from REE
REE_NAME_FIXES = {
    "LESCORTS 220": "LES CORTS 220",
    "R.CALDES 220": "RIERA DE CALDES 220",
    "S.FOST 220": "SANT FOST 220",
    "TANGER (CATALUÑA) 220": "TANGER CATALUÑA 220",
}
# CNMC upstream values that name no node
UPSTREAM_PLACEHOLDERS = {"*", "", "nan"}

# (region, "dso | id", REE "Código de subestación") -> True to pair them,
# False to confirm they are different sites. Filled in after review.
MANUAL_PAIRS: dict[tuple[str, str, int], bool] = {
    # Merged on the user's decision (2026-10-22). Name and upstream agree, but the
    # points are further apart than MAX_DIST_M: e-distribución VANDELLOS is ~450 m
    # from REE's VANDELLOS 400 point, ASCO ~870 m from REE's ASCÓ points. Both sit
    # in nuclear-plant areas, where one site can spread over several yards.
    ("catalunya", "R1-299 4686060", 50636): True,  # VANDELLOS <-> VANDELLOS 400
    ("catalunya", "R1-299 470115765", 50060): True,  # ASCO <-> ASCÓ 400 / ASCÓ 220
}

CAT_TSO = "1 TSO"
CAT_BOTH = "2 TSO+DSO"
CAT_DSO = "3 DSO"
CONFIDENCE_ORDER = ["manual", "alta", "media"]

GENERIC_WORDS = (
    "SUBESTACIO|SUBESTACION|SUBSTACION|SIUBESTACIO|SET|ST|SE|ESTACIO|ESTACION|RECEPTORA|"
    "TRANSMISSORA|TRANSFORMADORA|ELECTRICA|CENTRAL|HIDROELECTRICA|DE|DEL|LA|LES|EL|ELS|"
    "D|L|LOS|LAS"
)


def _norm(name: str, drop_generic: bool = True) -> str:
    s = unicodedata.normalize("NFKD", str(name).upper())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"[^A-Z0-9 ]", " ", s.replace(".", " ").replace("_", " "))
    if drop_generic:
        s = re.sub(rf"\b({GENERIC_WORDS})\b", " ", s)
    return " ".join(s.split())


def name_similarity(a: str, b: str, a_may_be_longer: bool = True) -> float:
    """1.0 for the abbreviation patterns e-distribución uses, else a fuzzy ratio.

    e-distribución truncates names to 10 characters ("LAFORTUNAD"), abbreviates
    "Sant"/"Santa"/"Mas" to one letter ("S.JUST"), and glues words ("CANJARDI").
    a_may_be_longer=False stops "PLAZA II" from matching a plain "PLAZA".
    """
    tokens_a, tokens_b = _norm(a).split(), _norm(b).split()
    a_full, b_full = "".join(_norm(a, False).split()), "".join(_norm(b, False).split())
    a_core, b_core = "".join(tokens_a), "".join(tokens_b)
    if not a_core or not b_core:
        return 0.0
    if b_full.startswith(a_full) or b_core.startswith(a_core):
        return 1.0
    if a_may_be_longer and a_core.startswith(b_core):  # GRADO1 -> GRADO
        return 1.0
    if len(a_core) >= 4 and b_core.endswith(a_core):  # TORRERO -> MONTETORRERO
        return 1.0
    if (
        len(tokens_a) >= 2 and len(tokens_a[0]) == 1 and tokens_b
        and tokens_b[0].startswith(tokens_a[0]) and tokens_a[1:] == tokens_b[1:]
    ):
        return 1.0
    return max(
        difflib.SequenceMatcher(None, a_core, b_core).ratio(),
        difflib.SequenceMatcher(None, a_full, b_full).ratio(),
    )


def same_name(a: str, b: str) -> bool:
    return name_similarity(a, b) >= 0.8


def haversine_m(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    h = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371000 * 2 * np.arcsin(np.sqrt(h))


def normalise_upstream(value) -> list[str]:
    """Upstream node names in REE's spelling ("La Canonja 220 kV" -> "LA CANONJA 220")."""
    out = []
    for part in str(value).split("/"):
        part = re.sub(r"\s*kV$", "", part.strip(), flags=re.IGNORECASE).upper()
        if part not in UPSTREAM_PLACEHOLDERS and part.upper() != "NAN":
            out.append(REE_NAME_FIXES.get(part, part))
    return out


# --- TSO side ----------------------------------------------------------------

def load_osm() -> pd.DataFrame:
    rows = []
    for path in sorted(OSM_DIR.glob("*_220_400kv.json")):
        for el in json.loads(path.read_text(encoding="utf-8"))["elements"]:
            center = el.get("center", el)
            tags = el["tags"]
            rows.append({
                "osm | id": f"{el['type']}/{el['id']}",
                "osm | name": tags.get("name", ""),
                "osm | operator": tags.get("operator", ""),
                "osm | lat": center["lat"],
                "osm | lon": center["lon"],
            })
    return pd.DataFrame(rows).drop_duplicates("osm | id").reset_index(drop=True)


def load_cnmc_transmission(region_key: str) -> pd.DataFrame:
    """CNMC's point for each REE node, keyed by REE's exact node name."""
    df = pd.read_csv(CLEAN_DIR / f"cnmc_generacion_transporte_{region_key}.csv")
    df[NODE_COL] = df["NUDO_AFECCION_RDT"].str.strip()
    return df[[NODE_COL, "lat", "lon", "MUNICIPIO"]]


def load_tso_sites(region_key: str, region_label: str, osm: pd.DataFrame) -> pd.DataFrame:
    """One row per REE substation code in the region, located through CNMC, else OSM."""
    gen = read_sheet(REE_FILES["generacion"])
    dem = read_sheet(REE_FILES["demanda"])
    dist_pos = dem.set_index(NODE_COL)[[
        "POSICIONES | A red de distribución | E", "POSICIONES | A red de distribución | P",
    ]].sum(axis=1, min_count=1)
    nodes = gen[gen["Comunidad Autónoma"] == region_label][[NODE_COL, "Código Subestación"]].copy()
    nodes["dist_pos"] = nodes[NODE_COL].map(dist_pos)
    nodes["kv"] = nodes[NODE_COL].str.rsplit(" ", n=1).str[1].astype(int)
    nodes = nodes.merge(load_cnmc_transmission(region_key), on=NODE_COL, how="left")
    # main node first: highest voltage, then the plain name before a "(X B)" half
    nodes = nodes.sort_values(["Código Subestación", "kv", NODE_COL], ascending=[True, False, True])

    rows = []
    for code, g in nodes.groupby("Código Subestación", sort=False):
        located = g.dropna(subset=["lat"])
        spread = haversine_m(
            located["lat"].values[:, None], located["lon"].values[:, None],
            located["lat"].values[None, :], located["lon"].values[None, :],
        ).max() if len(located) > 1 else 0.0
        rows.append({
            "ree | Código de subestación": code,
            "ree | nudos": "; ".join(g[NODE_COL]),
            "ree | nombre": g[NODE_COL].iloc[0].rsplit(" ", 1)[0],
            "ree | tensiones_kv": ";".join(map(str, sorted(set(g["kv"])))),
            "ree | posiciones a red de distribución": g["dist_pos"].sum(),
            "cnmc | lat": located["lat"].iloc[0] if len(located) else np.nan,
            "cnmc | lon": located["lon"].iloc[0] if len(located) else np.nan,
            "cnmc | municipio": located["MUNICIPIO"].iloc[0] if len(located) else "",
            "cnmc | dispersion_m": round(spread) if len(located) else np.nan,
            "_pts": list(zip(located["lat"], located["lon"])),
        })
    sites = pd.DataFrame(rows)

    # OSM only for sites CNMC doesn't locate
    missing = sites["cnmc | lat"].isna()
    osm_cols = ["osm | id", "osm | name", "osm | lat", "osm | lon", "osm | ubicado_por"]
    osm_found = pd.DataFrame(
        [locate_in_osm(n, osm) if m else _no_osm() for n, m in zip(sites["ree | nombre"], missing)],
        index=sites.index,
    )[osm_cols]
    sites = pd.concat([sites, osm_found], axis=1)
    return _set_tso_location(sites)


def _no_osm() -> dict:
    return {"osm | id": "", "osm | name": "", "osm | lat": np.nan, "osm | lon": np.nan, "osm | ubicado_por": ""}


def _set_tso_location(sites: pd.DataFrame) -> pd.DataFrame:
    """Fill "tso | ubicacion" and the point list used for distances."""
    has_cnmc = sites["cnmc | lat"].notna()
    has_osm = sites["osm | lat"].notna()
    sites["tso | ubicacion"] = np.select(
        [has_cnmc, has_osm], ["cnmc", "osm " + sites["osm | ubicado_por"]], ""
    )
    sites["_pts"] = [
        pts if c else ([(la, lo)] if o else [])
        for pts, c, o, la, lo in zip(sites["_pts"], has_cnmc, has_osm, sites["osm | lat"], sites["osm | lon"])
    ]
    return sites


def locate_in_osm(name: str, osm: pd.DataFrame) -> dict:
    score = osm["osm | name"].map(lambda o: name_similarity(name, o, a_may_be_longer=False) if o else 0.0)
    cand = osm[score >= OSM_NAME_MIN]
    exact = cand[cand["osm | name"].map(lambda o: _norm(o) == _norm(name))]
    if len(exact):  # "RUBI" is Rubí, not Rubió
        cand = exact
    if len(cand) > 1:
        ree_op = cand[cand["osm | operator"].str.contains("Red Eléctrica|REE", case=False)]
        if len(ree_op):
            cand = ree_op
    if cand.empty:
        return _no_osm()
    spread = haversine_m(
        cand["osm | lat"].values[:, None], cand["osm | lon"].values[:, None],
        cand["osm | lat"].values[None, :], cand["osm | lon"].values[None, :],
    ).max()
    if spread > OSM_SPREAD_MAX_M:  # same name, different places: can't tell which
        return _no_osm()
    return {
        "osm | id": "; ".join(cand["osm | id"]),
        "osm | name": "; ".join(dict.fromkeys(cand["osm | name"])),
        "osm | lat": cand["osm | lat"].mean(),
        "osm | lon": cand["osm | lon"].mean(),
        "osm | ubicado_por": "nombre",
    }


def locate_by_upstream(tso: pd.DataFrame, dso: pd.DataFrame, osm: pd.DataFrame) -> pd.DataFrame:
    """Locate TSO sites neither CNMC nor an OSM name placed, through their DSO children.

    If a DSO site that names an unlocated TSO site as upstream sits within
    MAX_DIST_M of an OSM 220/400 kV substation no other TSO site uses, that
    substation is taken as the TSO site's location. Skipped when it isn't unique.
    """
    tso = tso.copy()
    unlocated = set(tso.loc[tso["tso | ubicacion"] == "", "ree | Código de subestación"])
    if not unlocated:
        return tso
    claimed = {i for ids in tso["osm | id"] for i in ids.split("; ") if i}
    free = osm[~osm["osm | id"].isin(claimed)].reset_index(drop=True)
    dist = haversine_m(
        dso["dso | lat"].values[:, None], dso["dso | lon"].values[:, None],
        free["osm | lat"].values[None, :], free["osm | lon"].values[None, :],
    )
    node_to_site = _node_to_site(tso)
    found: dict[int, set[int]] = {}
    for i, d in dso.iterrows():
        for node in d["_up"]:
            site = node_to_site.get(node)
            if site not in unlocated or (dist[i] > MAX_DIST_M).all():
                continue
            found.setdefault(site, set()).add(int(np.argmin(dist[i])))
    osm_use = pd.Series([j for js in found.values() for j in js]).value_counts()
    for site, js in found.items():
        if len(js) != 1 or osm_use[next(iter(js))] > 1:
            continue
        o = free.iloc[next(iter(js))]
        row = tso.index[tso["ree | Código de subestación"] == site]
        tso.loc[row, ["osm | id", "osm | name", "osm | lat", "osm | lon", "osm | ubicado_por"]] = [
            o["osm | id"], o["osm | name"], o["osm | lat"], o["osm | lon"], "aguas arriba",
        ]
    return _set_tso_location(tso)


def _node_to_site(tso: pd.DataFrame) -> dict[str, int]:
    return {
        node: code
        for code, nodes in zip(tso["ree | Código de subestación"], tso["ree | nudos"])
        for node in nodes.split("; ")
    }


# --- DSO side ----------------------------------------------------------------

def load_dso_sites(region_key: str) -> pd.DataFrame:
    """One row per distribution substation: e-distribución plus CNMC's other DSOs."""
    nodes = pd.read_csv(CLEAN_DIR / f"nodos_{region_key}.csv")
    nodes["_up"] = nodes[UPSTREAM_COL].map(lambda v: normalise_upstream(v) if pd.notna(v) else [])
    edis = nodes.groupby("edis | Subestación").agg(**{
        "dso | nombre": ("edis | Nombre Subestación", "first"),
        "dso | tensiones_kv": ("edis | Nivel de Tensión (kV)", lambda s: ";".join(map(str, sorted(set(s))))),
        "dso | lat": ("edis | lat", "first"),
        "dso | lon": ("edis | lon", "first"),
        "_up": ("_up", lambda s: sorted({u for lst in s for u in lst})),
    }).reset_index()
    edis["dso | id"] = EDIS_GESTOR + " " + edis.pop("edis | Subestación").astype(str)
    edis["dso | gestor"] = EDIS_NAME
    edis["dso | fuente"] = "edis"
    edis["dso | coordenadas_corregidas"] = False

    cnmc = pd.concat(
        [pd.read_csv(CLEAN_DIR / f"cnmc_{k}_distribucion_{region_key}.csv") for k in ("generacion", "demanda")],
        ignore_index=True,
    )
    cnmc = cnmc[cnmc["GESTOR_RED"] != EDIS_GESTOR]
    upstream = cnmc["NUDO_AFECCION_RDT"] if "NUDO_AFECCION_RDT" in cnmc else pd.Series(np.nan, index=cnmc.index)
    cnmc["_up"] = upstream.map(lambda v: normalise_upstream(v) if pd.notna(v) else [])
    others = cnmc.groupby(["GESTOR_RED", "SUBESTACION"]).agg(**{
        "dso | gestor": ("DESCRIPCION", "first"),
        "dso | tensiones_kv": ("NIVEL_TENSION", lambda s: ";".join(map(str, sorted(set(s))))),
        "dso | lat": ("lat", "first"),
        "dso | lon": ("lon", "first"),
        "dso | coordenadas_corregidas": ("coordenadas_corregidas", "any"),
        "_up": ("_up", lambda s: sorted({u for lst in s for u in lst})),
    }).reset_index()
    others["dso | id"] = others["GESTOR_RED"] + " " + others["SUBESTACION"]
    others["dso | nombre"] = others.pop("SUBESTACION")
    others = others.drop(columns="GESTOR_RED")
    others["dso | fuente"] = "cnmc"

    cols = ["dso | id", "dso | gestor", "dso | fuente", "dso | nombre", "dso | tensiones_kv",
            "dso | lat", "dso | lon", "dso | coordenadas_corregidas", "_up"]
    dso = pd.concat([edis[cols], others[cols]], ignore_index=True)
    dso["dso | nudos aguas arriba"] = dso["_up"].map("; ".join)
    return dso


# --- pairing -----------------------------------------------------------------

def pair_sites(region_key: str, tso: pd.DataFrame, dso: pd.DataFrame) -> pd.DataFrame:
    """Every plausible (DSO site, TSO site) pair with its evidence and verdict."""
    node_to_site = _node_to_site(tso)
    rows = []
    for _, d in dso.iterrows():
        upstream_sites = {node_to_site.get(n) for n in d["_up"]}
        for _, t in tso.iterrows():
            name_ok = same_name(d["dso | nombre"], t["ree | nombre"])
            up_ok = t["ree | Código de subestación"] in upstream_sites
            dist = min(
                (haversine_m(d["dso | lat"], d["dso | lon"], la, lo) for la, lo in t["_pts"]),
                default=np.nan,
            )
            near = dist <= MAX_DIST_M
            if near and (name_ok or up_ok):
                verdict = "media" if t["tso | ubicacion"] == "osm aguas arriba" else "alta"
            elif np.isnan(dist) and name_ok and up_ok:
                verdict = "media"
            elif name_ok and up_ok:
                verdict = "a revisar"
            else:
                continue
            manual = MANUAL_PAIRS.get((region_key, d["dso | id"], int(t["ree | Código de subestación"])))
            if manual is not None:
                verdict = "manual" if manual else "manual: distintas"
            rows.append({
                "dso | id": d["dso | id"],
                "ree | Código de subestación": t["ree | Código de subestación"],
                "distancia_m": round(dist) if not np.isnan(dist) else np.nan,
                "nombre_similar": name_ok,
                "aguas_arriba": up_ok,
                "confianza": verdict,
            })
    return pd.DataFrame(rows)


def _evidence(row) -> str:
    dist = "sin coordenadas TSO" if pd.isna(row["distancia_m"]) else f"{row['distancia_m']:.0f} m"
    kinds = [k for k, ok in (("nombre", row["nombre_similar"]), ("aguas arriba", row["aguas_arriba"])) if ok]
    return f"{row['dso | nombre']}: {dist}, {' + '.join(kinds)}"


def build_sites(region_key: str, tso: pd.DataFrame, dso: pd.DataFrame, pairs: pd.DataFrame) -> pd.DataFrame:
    paired = pairs[pairs["confianza"].isin(CONFIDENCE_ORDER)]
    dup = paired["dso | id"].duplicated(keep=False)
    if dup.any():
        raise ValueError(f"{region_key}: a DSO site is paired with more than one TSO site:\n{paired[dup]}")

    tso_cols = [c for c in tso.columns if not c.startswith("_")]
    dso_cols = [c for c in dso.columns if not c.startswith("_")]
    joined = paired.merge(dso[dso_cols], on="dso | id")
    joined["evidencia"] = joined.apply(_evidence, axis=1)
    joined["_rank"] = joined["confianza"].map(CONFIDENCE_ORDER.index)

    def collapse(g: pd.DataFrame) -> pd.Series:
        """One row per TSO site: its DSO sites joined with "; "."""
        out = {c: "; ".join(map(str, g[c])) for c in dso_cols if c not in ("dso | lat", "dso | lon")}
        out["dso | lat"] = g["dso | lat"].iloc[0]
        out["dso | lon"] = g["dso | lon"].iloc[0]
        out["confianza"] = CONFIDENCE_ORDER[g["_rank"].max()]  # weakest pairing at the site
        out["distancia_m"] = g["distancia_m"].max()
        out["evidencia"] = "; ".join(g["evidencia"])
        out["dso | n_sitios"] = len(g)
        return pd.Series(out)

    both = joined.groupby("ree | Código de subestación").apply(collapse, include_groups=False).reset_index()
    both = both.merge(tso[tso_cols], on="ree | Código de subestación")
    both["categoria"] = CAT_BOTH

    review = pairs[
        (pairs["confianza"] == "a revisar")
        & ~pairs["dso | id"].isin(paired["dso | id"])
        & ~pairs["ree | Código de subestación"].isin(paired["ree | Código de subestación"])
    ]
    tso_only = tso[~tso["ree | Código de subestación"].isin(paired["ree | Código de subestación"])][tso_cols].copy()
    tso_only["categoria"] = CAT_TSO
    dso_only = dso[~dso["dso | id"].isin(paired["dso | id"])][dso_cols].copy()
    dso_only["categoria"] = CAT_DSO
    dso_only["dso | n_sitios"] = 1
    for df, key in ((tso_only, "ree | Código de subestación"), (dso_only, "dso | id")):
        df["confianza"] = np.where(df[key].isin(review[key]), "a revisar", "")

    sites = pd.concat([both, tso_only, dso_only], ignore_index=True)
    # one location per site: the TSO point where there is one, else the DSO's
    tso_lat = sites["cnmc | lat"].fillna(sites["osm | lat"])
    tso_lon = sites["cnmc | lon"].fillna(sites["osm | lon"])
    sites["lat"] = tso_lat.fillna(sites["dso | lat"])
    sites["lon"] = tso_lon.fillna(sites["dso | lon"])
    sites["fuente_coordenadas"] = np.select(
        [sites["cnmc | lat"].notna(), sites["osm | lat"].notna(), sites["dso | lat"].notna()],
        ["cnmc", "osm", sites["dso | fuente"].astype(str)],
        "",
    )

    front = ["categoria", "confianza", "distancia_m", "evidencia", "lat", "lon", "fuente_coordenadas"]
    sites = sites[front + tso_cols + dso_cols + ["dso | n_sitios"]]
    return sites.sort_values(["categoria", "ree | nombre", "dso | nombre"]).reset_index(drop=True)


def main() -> None:
    osm = load_osm()
    for region_key, region_label in REGIONS.items():
        tso = load_tso_sites(region_key, region_label, osm)
        dso = load_dso_sites(region_key)
        tso = locate_by_upstream(tso, dso, osm)
        pairs = pair_sites(region_key, tso, dso)
        sites = build_sites(region_key, tso, dso, pairs)

        out_path = CLEAN_DIR / f"subestaciones_{region_key}.csv"
        sites.to_csv(out_path, index=False)
        located = tso["tso | ubicacion"].replace("", "sin ubicar").value_counts().to_dict()
        counts = sites.groupby(["categoria", "confianza"]).size().to_dict()
        print(f"{region_key}: {len(tso)} TSO sites {located}, "
              f"{len(dso)} DSO sites ({dso['dso | fuente'].value_counts().to_dict()}) "
              f"-> {len(sites)} sites {counts} -> {out_path}")


if __name__ == "__main__":
    main()
