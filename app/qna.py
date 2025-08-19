import re
import pandas as pd
from typing import List, Dict, Any, Optional
from difflib import get_close_matches

QUESTION_RE = re.compile(r"([^?.!]*\?)(?:\s|$)", re.MULTILINE)

def extract_questions(text: str) -> List[str]:
    """
    Extract questions from free-form text.
    Captures '?' endings and Q: style.
    """
    # Split by question marks and Q markers
    parts = re.split(r'(?<=\?)|\bQ\d*[:.)]', text)
    qs = []
    for p in parts:
        p = p.strip()
        if len(p.split()) >= 3 and p.endswith("?"):
            qs.append(p)

    # Deduplicate while preserving order
    seen, out = set(), []
    for q in qs:
        low = q.lower()
        if low not in seen:
            seen.add(low)
            out.append(q)
    return out


def classify_question(q: str, has_csv: bool, columns: Optional[List[str]] = None) -> str:
    """
    Hybrid classifier: checks CSV columns, keywords, then defaults to web.
    """
    ql = q.lower()
    if has_csv and columns:
        # Column name match
        for col in columns:
            if col.lower() in ql:
                return "csv"

    cues = [
        "in the dataset", "in the csv", "average", "count", "top",
        "group", "mean", "sum", "unique", "by ", "total", "median",
        "correlation", "chart", "plot", "graph", "trend"
    ]
    if has_csv and any(c in ql for c in cues):
        return "csv"

    return "web"


def _match_column(text: str, columns: List[str]) -> Optional[str]:
    """Fuzzy match text fragment against dataframe columns."""
    matches = get_close_matches(text.lower(), [c.lower() for c in columns], n=1, cutoff=0.6)
    if matches:
        for c in columns:
            if c.lower() == matches[0]:
                return c
    return None


def plan_csv_op(q: str, df: pd.DataFrame) -> Dict[str, Any]:
    """
    Create a heuristic CSV operation plan from question.
    Uses fuzzy matching on dataframe columns.
    """
    ql = q.lower()
    cols = list(df.columns)

    # Count rows
    if "row" in ql and "count" in ql:
        return {"kind": "count_rows"}

    # Look for a numeric column
    num_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
    text_cols = [c for c in cols if df[c].dtype == "object"]

    # Total of some column
    if "total" in ql or "sum" in ql:
        target = _match_column("sales", cols) or (num_cols[0] if num_cols else None)
        if target:
            return {"kind": "sum", "col": target}

    # Median
    if "median" in ql:
        target = _match_column("sales", cols) or (num_cols[0] if num_cols else None)
        if target:
            return {"kind": "median", "col": target}

    # Correlation
    if "correlation" in ql:
        if len(num_cols) >= 2:
            return {"kind": "correlation", "col_x": num_cols[0], "col_y": num_cols[1]}

    # Group & top
    if "highest" in ql or "top" in ql:
        group_col = _match_column("region", cols) or (text_cols[0] if text_cols else None)
        sum_col = _match_column("sales", cols) or (num_cols[0] if num_cols else None)
        if group_col and sum_col:
            return {"kind": "group_sum_top", "group_col": group_col, "sum_col": sum_col}

    # Charts
    if "bar chart" in ql:
        return {"kind": "bar_chart", "x": text_cols[0], "y": num_cols[0]} if text_cols and num_cols else {"kind": "count_rows"}
    if "line chart" in ql or "trend" in ql:
        return {"kind": "line_chart", "x": cols[0], "y": num_cols[0]} if num_cols else {"kind": "count_rows"}

    # Default
    return {"kind": "count_rows"}
