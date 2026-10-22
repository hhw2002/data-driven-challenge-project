"""Merge e-distribución and REE capacity data into one table per region.

One row per e-distribución node (substation x voltage level). Each row
carries that node's demand and generation capacity from e-distribución,
plus the capacity situation of its upstream transmission node from REE,
linked through e-distribución's "Nudo Afección RdT" column.

Every column name starts with the source it came from:
- "edis | ..."      e-distribución, same in the demand and generation files
- "edis_dem | ..."  e-distribución demand file
- "edis_gen | ..."  e-distribución generation file
- "ree | ..."       REE, same in the demand and generation files
- "ree_dem | ..."   REE demand file
- "ree_gen | ..."   REE generation file
The only unprefixed column is "enlace_ree", which this script adds to say
how the row was linked to REE (see LINK_* below).

The REE lookup uses the national table, not the per-region clean files:
some nodes hang off a transmission node in a neighbouring region.
"""
from pathlib import Path

import pandas as pd

from filter_ree_transporte import FILES as REE_FILES
from filter_ree_transporte import NODE_COL, read_sheet

PROJECT_DIR = Path(__file__).resolve().parent.parent
CLEAN_DIR = PROJECT_DIR / "data" / "grid" / "clean"

REGIONS = ["catalunya"]

KEY = ["Subestación", "Nivel de Tensión (kV)"]
UPSTREAM_COL = "Nudo Afección RdT"

# e-distribución columns that only exist in, or differ between, its two files
EDIS_PER_FILE = {
    "dem": [
        "Capacidad firme disponible (MW)",
        "Capacidad de acceso firme de demanda ocupada (MW)",
        "Capacidad de acceso firme admitida y no evaluada (MW)",
        "Comentarios",
    ],
    "gen": [
        "Capacidad disponible (MW)",
        "Capacidad ocupada (MW)",
        "Capacidad admitida y no resuelta (MW)",
        UPSTREAM_COL,
        "Nudo limitado por Scc ",
        "Comentarios",
    ],
}

# e-distribución spells a few transmission nodes differently from REE
REE_NAME_FIXES = {
    "LESCORTS 220": "LES CORTS 220",
    "R.CALDES 220": "RIERA DE CALDES 220",
    "S.FOST 220": "SANT FOST 220",
    "TANGER (CATALUÑA) 220": "TANGER CATALUÑA 220",
}

REE_SHARED = [NODE_COL, "Comunidad Autónoma"]

# REE columns to carry over, picked by the header section they sit under
REE_SECTIONS = {
    "gen": [
        "MARGEN DE CAPACIDAD DE ACCESO TOTAL |",
        "CRITERIOS LIMITANTES | Generación",
        "CRITERIOS LIMITANTES | Almacenamiento",
        "CAPACIDAD DE ACCESO NO DISPONIBLE PARA SOLICITUDES A LA RED DE TRANSPORTE Y ACEPTABILIDADES | Motivo",
        "CAPACIDAD DE ACCESO DISPONIBLE PARA SOLICITUDES A LA RED DE TRANSPORTE Y ACEPTABILIDADES |",
        "Motivo de reserva de capacidad de acceso en el nudo",
    ],
    "dem": [
        "SITUACIÓN NUDO CAPACIDAD DE ACCESO OTORGADA | Capacidad de acceso para consumo en la RdD (valor de referencia)",
        "SITUACIÓN NUDO CAPACIDAD DE ACCESO OTORGADA | Estado acuerdo",
        "MARGEN CAPACIDAD DE ACCESO TOTAL PARA CONEXIÓN A LA RDT |",
        "MARGEN CAPACIDAD DE ACCESO TOTAL PARA CONEXIÓN A LA RDD |",
        "CRITERIO LIMITANTE RDT |",
        "CRITERIO LIMITANTE RDD |",
        "Motivo capacidad no otorgable en RdT",
        "CAPACIDAD DE ACCESO DISPONIBLE PARA SOLICITUDES CRITERIO GENERAL RDT |",
        "CAPACIDAD DE ACCESO DISPONIBLE PARA SOLICITUDES CRITERIO GENERAL RDD |",
        "Nudo de concurso",
    ],
}

LINK_EXACT = "exacto"  # upstream name found as-is in REE
LINK_FIXED = "nombre corregido"  # found after applying REE_NAME_FIXES
LINK_TWO = "dos nudos"  # e-distribución names two upstream nodes: REE columns left empty
LINK_NONE = "sin nudo"  # no usable upstream node name


def load_edis(region_key: str) -> pd.DataFrame:
    """Join the region's demand and generation files, one row per node."""
    dem = pd.read_csv(CLEAN_DIR / f"demanda_{region_key}.csv")
    gen = pd.read_csv(CLEAN_DIR / f"generacion_{region_key}.csv")

    shared = [c for c in dem.columns if c not in EDIS_PER_FILE["dem"]]
    # shared columns are taken from the demand file
    out = dem[shared].rename(columns=lambda c: f"edis | {c.strip()}")
    for kind, df in (("dem", dem), ("gen", gen)):
        part = df[KEY + EDIS_PER_FILE[kind]].rename(
            columns={c: f"edis_{kind} | {c.strip()}" for c in EDIS_PER_FILE[kind]}
        )
        part = part.rename(columns={c: f"edis | {c}" for c in KEY})
        out = out.merge(part, on=[f"edis | {c}" for c in KEY], validate="one_to_one")
    return out


def load_ree() -> pd.DataFrame:
    """National REE table: one row per transmission node, selected columns."""
    out = None
    for kind, sections in REE_SECTIONS.items():
        df = read_sheet(REE_FILES["demanda" if kind == "dem" else "generacion"])
        keep = [c for c in df.columns if any(c.startswith(s) for s in sections)]
        part = df[REE_SHARED + keep].rename(columns={c: f"ree_{kind} | {c}" for c in keep})
        out = part if out is None else out.merge(part, on=REE_SHARED, validate="one_to_one")
    return out.rename(columns={c: f"ree | {c}" for c in REE_SHARED})


def resolve_upstream(value) -> tuple[str | None, str]:
    """Map an e-distribución upstream value to (REE node name, link status)."""
    if pd.isna(value):
        return None, LINK_NONE
    parts = [p.strip() for p in str(value).split("/")]
    fixed = [REE_NAME_FIXES.get(p, p) for p in parts]
    if len(parts) > 1:
        return " / ".join(fixed), LINK_TWO
    return fixed[0], LINK_FIXED if fixed != parts else LINK_EXACT


def main() -> None:
    ree = load_ree()
    ree_key = f"ree | {NODE_COL}"
    known = set(ree[ree_key])

    for region_key in REGIONS:
        nodes = load_edis(region_key)
        resolved = nodes[f"edis_gen | {UPSTREAM_COL}"].map(resolve_upstream)
        nodes[ree_key] = resolved.str[0]
        nodes["enlace_ree"] = resolved.str[1]
        # a single name REE doesn't list (e.g. "A determinar") is no link at all
        single = nodes["enlace_ree"].isin([LINK_EXACT, LINK_FIXED])
        nodes.loc[single & ~nodes[ree_key].isin(known), "enlace_ree"] = LINK_NONE

        merged = nodes.merge(ree, on=ree_key, how="left", validate="many_to_one")
        link = merged.pop("enlace_ree")
        merged.insert(merged.columns.get_loc(ree_key), "enlace_ree", link)

        out_path = CLEAN_DIR / f"nodos_{region_key}.csv"
        merged.to_csv(out_path, index=False)
        counts = ", ".join(f"{k}: {v}" for k, v in link.value_counts().items())
        print(f"{region_key}: {len(merged)} nodes, {len(merged.columns)} columns ({counts}) -> {out_path}")


if __name__ == "__main__":
    main()
