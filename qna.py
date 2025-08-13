import re
from typing import List, Dict, Any, Optional
import pandas as pd

QUESTION_RE = re.compile(r"([^\n?.!]*\?)(?:\s|$)")

def extract_questions(text: str) -> List[str]:
    qs = [m.group(1).strip() for m in QUESTION_RE.finditer(text)]
    seen, out = set(), []
    for q in qs:
        k = q.lower()
        if k not in seen:
            seen.add(k)
            out.append(q)
    return out

CSV_CUES = [
    "in the dataset", "in the csv", "according to the data",
    "average", "count", "top", "group", "trend", "correlation", "by column",
    "mean", "sum", "median", "min", "max", "unique"
]

def classify_question(q: str, has_csv: bool) -> str:
    if has_csv and any(tok in q.lower() for tok in CSV_CUES):
        return "csv"
    # fallback could try to detect entities; MVP defaults to web otherwise
    return "web"

def plan_csv_op(q: str, df: pd.DataFrame) -> Dict[str, Any]:
    ql = q.lower()
    # simplest intents first
    if "row" in ql and "count" in ql:
        return {"kind": "count_rows"}

    for col in df.columns:
        cl = str(col).lower()
        if f"unique {cl}" in ql or ("unique" in ql and cl in ql):
            return {"kind": "nunique", "col": col}

    # groupby mean/sum/count pattern
    agg = None
    if "mean" in ql or "average" in ql:
        agg = "mean"
    elif "sum" in ql:
        agg = "sum"
    elif "count" in ql:
        agg = "count"

    # find a candidate group column by “by <col>”
    by_col = None
    m = re.search(r"by ([A-Za-z0-9_ ]+)", ql)
    if m:
        # match to an actual column if possible
        token = m.group(1).strip()
        # simple fuzzy: exact case-insensitive match
        for col in df.columns:
            if str(col).lower() == token:
                by_col = col
                break

    # metric column
    metric_col = None
    for col in df.columns:
        if str(col).lower() in ql and df[col].dtype.kind in "ifu":
            metric_col = col
            break

    if by_col and agg and (agg == "count" or metric_col is not None):
        return {
            "kind": "groupby_agg",
            "by": by_col,
            "metric": metric_col,
            "agg": agg
        }

    # top-k pattern
    if "top" in ql or "largest" in ql:
        k = 5
        mk = re.search(r"top (\d+)", ql)
        if mk:
            k = int(mk.group(1))
        # find numeric column mentioned
        num_cols = [c for c in df.columns if df[c].dtype.kind in "ifu"]
        for col in df.columns:
            if str(col).lower() in ql and col in num_cols:
                return {"kind": "topk", "col": col, "k": k, "ascending": False}
        # fallback: first numeric column
        if num_cols:
            return {"kind": "topk", "col": num_cols[0], "k": k, "ascending": False}

    # default safe op
    return {"kind": "count_rows"}
