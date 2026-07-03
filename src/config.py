"""
Loader do config.yaml (raiz do projeto) — fonte única dos hiperparâmetros usados
por src/ e app/.
"""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

with open(ROOT / "config.yaml", encoding="utf-8") as _f:
    CONFIG: dict = yaml.safe_load(_f)
