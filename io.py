from pathlib import Path
import pandas as pd
from typing import Optional

def load_txt(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"TXT not found: {path}")
    return p.read_text(encoding="utf-8", errors="ignore")

def load_csv_optional(path: Optional[str]) -> Optional[pd.DataFrame]:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    return pd.read_csv(p)
