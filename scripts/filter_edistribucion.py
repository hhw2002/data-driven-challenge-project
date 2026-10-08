"""Filter e-distribución capacity data (raw) into per-region clean CSVs.

Splits the demand and generation files into data/clean/aragon/ and
data/clean/catalunya/, dropping the duplicate code/label columns that
the source file repeats (Provincia, Municipio).
"""
from pathlib import Path

import pandas as pd

from geo_utils import utm_to_latlon

PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "data" / "raw" / "edistribucion_capacidad"
CLEAN_DIR = PROJECT_DIR / "data" / "clean"

FILES = {
    "demanda": RAW_DIR / "2026_09_demanda_edistribucion.xlsx",
    "generacion": RAW_DIR / "2026_09_generacion_edistribucion.xlsx",
}

REGIONS = {
    "aragon": "Aragón",
    "catalunya": "Catalunya",
}

RENAME = {
    "Provincia": "provincia_codigo",
    "Municipio": "municipio_codigo",
    "Provincia.1": "provincia",
    "Municipio.1": "municipio",
}


def load_and_clean(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path)
    return df.rename(columns=RENAME)


def main() -> None:
    for region_key, region_label in REGIONS.items():
        region_dir = CLEAN_DIR / region_key
        region_dir.mkdir(parents=True, exist_ok=True)
        for kind, path in FILES.items():
            df = load_and_clean(path)
            subset = df[df["Comunidad Autónoma"].str.contains(region_label, na=False)].copy()
            subset["lat"], subset["lon"] = utm_to_latlon(
                subset["Coordenada UTM X"], subset["Coordenada UTM Y"]
            )
            out_path = region_dir / f"{kind}_{region_key}.csv"
            subset.to_csv(out_path, index=False)
            print(f"{region_key}/{kind}: {len(subset)} rows, {subset['nombre_subestacion' if 'nombre_subestacion' in subset.columns else 'Nombre Subestación'].nunique()} substations -> {out_path}")


if __name__ == "__main__":
    main()
