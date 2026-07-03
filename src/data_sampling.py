"""
Amostragem estratificada do dataset de reviews (Books_rating.csv, ~2.8GB) usando
DuckDB para não carregar o arquivo inteiro em memória.

Estratifica por `score` (nota 1-5) para manter a diversidade de sentimentos na
amostra, já que o dataset original é fortemente enviesado para notas altas.
"""

from pathlib import Path

import duckdb

from src.config import CONFIG

ROOT = Path(__file__).resolve().parents[1]
RATINGS_CSV = ROOT / "Books_rating.csv"
OUTPUT_PATH = ROOT / "data" / "processed" / "sample_raw.parquet"

_CFG = CONFIG["sampling"]


def sample_ratings(
    ratings_csv: Path = RATINGS_CSV,
    target_size: int = _CFG["target_sample_size"],
    output_path: Path = OUTPUT_PATH,
    seed: float = _CFG["seed"],
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    con.execute(f"SELECT setseed({seed / 2_147_483_647})")

    print("Contando linhas por nota (score) no CSV completo...")
    counts = con.execute(
        f"""
        SELECT score, COUNT(*) AS n
        FROM read_csv_auto('{ratings_csv.as_posix()}', header=True)
        GROUP BY score
        ORDER BY score
        """
    ).fetchdf()
    print(counts)

    total_rows = counts["n"].sum()
    counts["p"] = (target_size * (counts["n"] / total_rows) / counts["n"]).clip(upper=1.0)
    print(f"\nTotal de linhas no CSV: {total_rows:,}")
    print(f"Alvo de amostra: {target_size:,}")
    print(counts)

    case_expr = " ".join(
        f"WHEN score = {row.score} THEN {row.p}" for row in counts.itertuples()
    )

    print("\nExecutando amostragem (1 leitura completa do CSV)...")
    con.execute(
        f"""
        COPY (
            SELECT *
            FROM read_csv_auto('{ratings_csv.as_posix()}', header=True)
            WHERE random() < CASE {case_expr} ELSE 0 END
        ) TO '{output_path.as_posix()}' (FORMAT PARQUET)
        """
    )

    sampled = con.execute(f"SELECT COUNT(*) FROM read_parquet('{output_path.as_posix()}')").fetchone()[0]
    print(f"\nAmostra salva em {output_path} com {sampled:,} linhas.")
    con.close()
    return output_path


if __name__ == "__main__":
    sample_ratings()
